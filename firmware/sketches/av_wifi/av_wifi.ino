/*
 * WiFi audio + video stream for Seeed XIAO ESP32S3 Sense
 * The board creates its own WiFi network (AP_SSID / AP_PASSWORD) and listens
 * for one app on TCP port 5000 at 192.168.4.1.
 * Packets are the same as av_stream.ino:
 *   4-byte type + 8-byte timestamp (us since boot) + 4-byte length + data,
 *   all little-endian. Types: "AUDI" audio, "FRAM" JPEG frame,
 *   "STRT"/"STOP" recording started/stopped, "HELO" reply to 'S'.
 * Commands from the app (single characters):
 *   'S' hello, 'R' start recording, 'E' end recording, 'X' disconnecting.
 * The B (BOOT) button also starts/stops a recording once an app is connected.
 * Orange LED: slow flash = network up, no device joined; solid = a device has
 * joined; fast flash = recording. Status messages go to USB serial.
 * Requires ESP32 Arduino core 3.x with PSRAM set to "OPI PSRAM",
 * and the WiFi antenna attached.
*/

#include <WiFi.h>
#include <ESP_I2S.h>
#include "esp_camera.h"
#include "esp_timer.h"

// camera pins for XIAO ESP32S3 Sense (from CameraWebServer camera_pins.h)
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  10
#define SIOD_GPIO_NUM  40
#define SIOC_GPIO_NUM  39
#define Y9_GPIO_NUM    48
#define Y8_GPIO_NUM    11
#define Y7_GPIO_NUM    12
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    16
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM    17
#define Y2_GPIO_NUM    15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM  47
#define PCLK_GPIO_NUM  13

// onboard controls
#define BUTTON_PIN 0            // "B" (BOOT) button, LOW when pressed
#define LED_PIN    LED_BUILTIN  // orange user LED (GPIO 21), on when LOW

// do not change for best
#define SAMPLE_RATE         16000U
#define AUDIO_CHUNK_SAMPLES 512  // 32 ms of audio per packet
#define AUDIO_QUEUE_CHUNKS  32   // ~1 s of audio buffered while a video frame is being sent

// make changes as needed
#define AP_SSID      "XIAO-AV"
#define AP_PASSWORD  "xiaoav123"    // at least 8 characters
#define TCP_PORT     5000
#define VOLUME_GAIN  1              // multiplier, 1 = raw mic signal
#define FRAME_SIZE   FRAMESIZE_VGA  // 640x480; try QVGA for more fps, SVGA/HD for more detail
#define JPEG_QUALITY 12             // 0-63, lower = better quality but bigger frames
#define LED_BLINK_MS 250            // LED on/off time while recording
#define LED_WAIT_MS  1000           // LED on/off time while waiting for a device to join

struct AudioChunk {
  uint64_t timestamp_us;
  uint32_t bytes;
  int16_t samples[AUDIO_CHUNK_SAMPLES];
};

I2SClass i2s;
QueueHandle_t audio_queue;
WiFiServer server(TCP_PORT);
WiFiClient client;
volatile bool recording = false;
bool receiver_ready = false;  // the app has sent 'S'
volatile bool device_joined = false;  // at least one device is on the WiFi network

void fail(const char *msg, int err) {
  while (1) {
    Serial.printf("%s: 0x%x\n", msg, err);
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  // USB serial: drop output instead of waiting when no serial monitor is reading it.
  // Otherwise each print blocks until a timeout and the stream stalls for seconds.
  Serial.setTxTimeoutMs(0);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);  // LED off

  camera_config_t config = {};
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.ledc_timer   = LEDC_TIMER_0;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAME_SIZE;
  config.jpeg_quality = JPEG_QUALITY;
  config.fb_count     = 2;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_LATEST;  // always send the newest frame

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) fail("Camera init failed (is PSRAM enabled?)", err);
  // The camera driver warns on every dropped frame ("FB-OVF"), several times a second
  esp_log_level_set("cam_hal", ESP_LOG_ERROR);

  i2s.setPinsPdmRx(42, 41);  // PDM clock, PDM data
  if (!i2s.begin(I2S_MODE_PDM_RX, SAMPLE_RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO))
    fail("Failed to initialize I2S", 0);

  audio_queue = xQueueCreate(AUDIO_QUEUE_CHUNKS, sizeof(AudioChunk));
  if (audio_queue == NULL) fail("Audio queue alloc failed", 0);

  // Board's own WiFi network; power saving off because it adds long send delays
  if (!WiFi.softAP(AP_SSID, AP_PASSWORD)) fail("Failed to start WiFi network", 0);
  WiFi.setSleep(false);
  server.begin();
  server.setNoDelay(true);
  Serial.printf("WiFi network \"%s\" ready, app connects to %s:%d\n",
                AP_SSID, WiFi.softAPIP().toString().c_str(), TCP_PORT);

  // Mic reader on core 0; loop() (camera + WiFi) runs on core 1
  xTaskCreatePinnedToCore(audio_task, "audio", 4096, NULL, 5, NULL, 0);
}

// Reads the mic continuously so audio never drops while a video frame is being sent.
// The mic's own DMA buffer only holds ~90 ms, the queue holds ~1 s.
void audio_task(void *arg) {
  static AudioChunk chunk;

  // Drain samples buffered since i2s.begin() so timestamps line up with real time
  for (int i = 0; i < 8; i++)
    i2s.readBytes((char *)chunk.samples, sizeof(chunk.samples));
  uint64_t start_us = esp_timer_get_time();
  uint64_t samples_read = 0;

  while (true) {
    chunk.bytes = i2s.readBytes((char *)chunk.samples, sizeof(chunk.samples));

    // Drive the LED here because this loop runs every 32 ms without fail
    uint64_t now_ms = esp_timer_get_time() / 1000;
    bool led_on;
    if (recording) led_on = (now_ms / LED_BLINK_MS) % 2 == 0;
    else if (device_joined) led_on = true;
    else led_on = (now_ms / LED_WAIT_MS) % 2 == 0;
    digitalWrite(LED_PIN, led_on ? LOW : HIGH);

    size_t n = chunk.bytes / 2;
    if (n == 0) continue;

    // Timestamp from the sample count, so audio timing stays exact
    chunk.timestamp_us = start_us + samples_read * 1000000ULL / SAMPLE_RATE;
    samples_read += n;
    if (!recording) continue;

    // Apply gain with clipping instead of wrap-around
    for (size_t i = 0; i < n; i++) {
      int32_t v = (int32_t)chunk.samples[i] * VOLUME_GAIN;
      chunk.samples[i] = constrain(v, -32768, 32767);
    }
    xQueueSend(audio_queue, &chunk, 0);  // dropped if the queue is full
  }
}

// Header goes out in one write so it isn't split into tiny TCP packets
void send_packet(const char *type, uint64_t timestamp_us, const uint8_t *data, uint32_t len) {
  uint8_t header[16];
  memcpy(header, type, 4);
  memcpy(header + 4, &timestamp_us, 8);
  memcpy(header + 12, &len, 4);
  client.write(header, sizeof(header));
  if (len) client.write(data, len);
}

void send_queued_audio() {
  static AudioChunk chunk;
  while (xQueueReceive(audio_queue, &chunk, 0) == pdTRUE)
    send_packet("AUDI", chunk.timestamp_us, (uint8_t *)chunk.samples, chunk.bytes);
}

// True once per press of the B button, ignoring contact bounce
bool button_pressed() {
  static bool was_down = false;
  static uint32_t last_change = 0;
  bool down = digitalRead(BUTTON_PIN) == LOW;
  if (down != was_down && millis() - last_change > 50) {
    was_down = down;
    last_change = millis();
    return down;
  }
  return false;
}

void start_recording() {
  xQueueReset(audio_queue);  // don't send stale audio
  send_packet("STRT", esp_timer_get_time(), NULL, 0);
  recording = true;
  Serial.println("Recording started");
}

void stop_recording(bool notify) {
  if (!recording) return;
  recording = false;
  Serial.println("Recording stopped");
  if (!notify) return;
  send_queued_audio();
  send_packet("STOP", esp_timer_get_time(), NULL, 0);
}

void disconnect_app() {
  stop_recording(false);
  receiver_ready = false;
  client.stop();
  Serial.println("App disconnected");
}

void loop() {
  // Devices joined to the WiFi network (sets the LED state)
  bool joined = WiFi.softAPgetStationNum() > 0;
  if (joined != device_joined) {
    device_joined = joined;
    Serial.println(joined ? "Device joined WiFi network" : "No devices on WiFi network");
  }

  // A new app connection replaces the old one
  WiFiClient incoming = server.accept();
  if (incoming) {
    if (client.connected()) disconnect_app();
    client = incoming;
    client.setNoDelay(true);
    Serial.printf("App connected from %s\n", client.remoteIP().toString().c_str());
  }
  if (receiver_ready && !client.connected()) disconnect_app();

  // Commands from the app
  while (client.available()) {
    char c = client.read();
    if (c == 'S') {
      receiver_ready = true;
      send_packet("HELO", esp_timer_get_time(), NULL, 0);
    } else if (c == 'R') {
      if (receiver_ready && !recording) start_recording();
    } else if (c == 'E') {
      stop_recording(true);
    } else if (c == 'X') {
      disconnect_app();
    }
  }

  // B button toggles recording (ignored until the app is connected)
  if (button_pressed()) {
    if (recording) stop_recording(true);
    else if (receiver_ready) start_recording();
  }

  if (!recording) {
    // Keep taking frames while idle: otherwise the first esp_camera_fb_get() after
    // starting a recording waits out the driver's 4 s timeout, and video starts late
    camera_fb_t *idle_fb = esp_camera_fb_get();
    if (idle_fb) esp_camera_fb_return(idle_fb);
    delay(10);
    return;
  }

  // Send all audio that arrived, then one video frame
  send_queued_audio();
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return;
  uint64_t ts = (uint64_t)fb->timestamp.tv_sec * 1000000ULL + fb->timestamp.tv_usec;
  send_packet("FRAM", ts, fb->buf, fb->len);
  esp_camera_fb_return(fb);
}
