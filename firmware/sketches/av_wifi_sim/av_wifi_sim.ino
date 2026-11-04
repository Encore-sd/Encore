/*
 * Simulated capture cycle for Seeed XIAO ESP32S3 Sense, over the board's own WiFi network
 * Fork of av_wifi.ino that walks through the phases of the planned capture process, for
 * realistic power and stream tests:
 *   1. Pairing: WiFi network up, waiting for a receiver. Camera and mic are off.
 *   2. Snapshot: continuous audio plus one camera frame every SNAPSHOT_INTERVAL_MS.
 *      Starts automatically when a receiver connects.
 *   3. Continuous: audio plus frames as fast as the link allows.
 * The B (BOOT) button switches between snapshot and continuous; the receiver can too.
 * When the receiver disconnects, the board stops the camera and mic and goes back to pairing.
 *
 * The board creates its own WiFi network (AP_SSID / AP_PASSWORD) and listens for one
 * receiver on TCP port 5000 at 192.168.4.1.
 * Packets are the same as av_wifi.ino:
 *   4-byte type + 8-byte timestamp (us since boot) + 4-byte length + data, all little-endian.
 *   Types: "AUDI" audio, "FRAM" JPEG frame, "HELO" reply to 'S', and
 *   "MODE": the phase changed. Its data is text, "<phase>:<cause>", where phase is
 *   "snapshot" or "continuous" and cause is "start", "button" or "command".
 * Commands from the receiver (single characters):
 *   'S' hello (starts capture in snapshot mode), 'P' snapshot mode, 'C' continuous mode,
 *   'X' disconnecting.
 * Orange LED: slow flash = pairing; slow glow (fades up and down) = snapshot mode;
 * fast flash = continuous mode. The LED is dimmed with PWM on timer 0, so the camera's clock
 * is moved to timer 3 to keep the two apart.
 * Status messages go to USB serial.
 * Requires ESP32 Arduino core 3.x with PSRAM set to "OPI PSRAM", and the WiFi antenna attached.
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
#define SNAPSHOT_INTERVAL_MS 1500   // one frame this often in snapshot mode
#define LED_BLINK_MS 250            // LED on/off time in continuous mode
#define LED_WAIT_MS  1000           // LED on/off time while pairing
#define LED_GLOW_MS  3000           // one fade up and down in snapshot mode

// LED dimming (PWM). The core puts the LED on the first free PWM timer, timer 0, which the
// camera driver would also take for its clock without the core knowing. So the camera's
// clock runs on timer 3 / channel 7 instead (see camera_start).
#define LED_PWM_CHANNEL 0
#define LED_PWM_FREQ    5000        // Hz, far too fast to see
#define LED_PWM_BITS    10          // 0-1023: fine steps keep the dim end of the fade smooth
#define LED_MAX         ((1 << LED_PWM_BITS) - 1)

enum Phase { PAIRING, SNAPSHOT, CONTINUOUS };
const char *PHASE_NAMES[] = {"pairing", "snapshot", "continuous"};

struct AudioChunk {
  uint64_t timestamp_us;
  uint32_t bytes;
  int16_t samples[AUDIO_CHUNK_SAMPLES];
};

I2SClass i2s;
QueueHandle_t audio_queue;
WiFiServer server(TCP_PORT);
WiFiClient client;
volatile Phase phase = PAIRING;
volatile bool mic_on = false;     // set by loop(); the audio task starts and stops the mic
bool camera_on = false;
uint32_t last_snapshot_ms = 0;

// LED brightness 0 (off) to LED_MAX (full). The LED is on when its pin is LOW, so the
// PWM duty is inverted.
void led_set(uint32_t level) {
  ledcWrite(LED_PIN, LED_MAX - level);
}

// Snapshot mode: a smooth fade up and down. The cosine gives the in-and-out of a breath;
// squaring it makes the fade look even, since the eye is far more sensitive to changes
// in dim light than in bright light.
uint32_t glow_level(uint64_t now_ms) {
  float x = 0.5f - 0.5f * cosf(2 * PI * (now_ms % LED_GLOW_MS) / LED_GLOW_MS);
  return (uint32_t)(x * x * LED_MAX);
}

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
  if (!ledcAttachChannel(LED_PIN, LED_PWM_FREQ, LED_PWM_BITS, LED_PWM_CHANNEL)) fail("LED PWM setup failed", 0);
  led_set(0);

  audio_queue = xQueueCreate(AUDIO_QUEUE_CHUNKS, sizeof(AudioChunk));
  if (audio_queue == NULL) fail("Audio queue alloc failed", 0);

  // Board's own WiFi network; power saving off because it adds long send delays
  if (!WiFi.softAP(AP_SSID, AP_PASSWORD)) fail("Failed to start WiFi network", 0);
  WiFi.setSleep(false);
  server.begin();
  server.setNoDelay(true);
  Serial.printf("Pairing: WiFi network \"%s\" ready, receiver connects to %s:%d\n",
                AP_SSID, WiFi.softAPIP().toString().c_str(), TCP_PORT);

  // Mic reader on core 0; loop() (camera + WiFi) runs on core 1
  xTaskCreatePinnedToCore(audio_task, "audio", 4096, NULL, 5, NULL, 0);
}

// --- Camera: only running in snapshot and continuous mode ---

bool camera_start() {
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
  config.ledc_timer   = LEDC_TIMER_3;    // timer 0 / channel 0 are the LED's
  config.ledc_channel = LEDC_CHANNEL_7;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAME_SIZE;
  config.jpeg_quality = JPEG_QUALITY;
  config.fb_count     = 2;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_LATEST;  // always send the newest frame

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed (is PSRAM enabled?): 0x%x\n", err);
    return false;
  }
  // The camera driver warns on every dropped frame ("FB-OVF"), several times a second
  esp_log_level_set("cam_hal", ESP_LOG_ERROR);
  camera_on = true;
  return true;
}

void camera_stop() {
  if (!camera_on) return;
  esp_camera_deinit();
  camera_on = false;
}

// --- Audio: the mic only runs while capturing ---

// Reads the mic continuously so audio never drops while a video frame is being sent.
// The mic's own DMA buffer only holds ~90 ms, the queue holds ~1 s.
// This task also starts and stops the mic, so only one task ever touches it.
void audio_task(void *arg) {
  static AudioChunk chunk;
  bool running = false;
  uint64_t start_us = 0, samples_read = 0;

  while (true) {
    // Drive the LED here because this loop runs every 20-32 ms without fail
    uint64_t now_ms = esp_timer_get_time() / 1000;
    if (phase == CONTINUOUS) led_set((now_ms / LED_BLINK_MS) % 2 == 0 ? LED_MAX : 0);
    else if (phase == SNAPSHOT) led_set(glow_level(now_ms));
    else led_set((now_ms / LED_WAIT_MS) % 2 == 0 ? LED_MAX : 0);

    if (mic_on && !running) {
      i2s.setPinsPdmRx(42, 41);  // PDM clock, PDM data
      if (!i2s.begin(I2S_MODE_PDM_RX, SAMPLE_RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO)) {
        Serial.println("Failed to start the mic");
        vTaskDelay(pdMS_TO_TICKS(1000));
        continue;
      }
      // Drain samples buffered since i2s.begin() so timestamps line up with real time
      for (int i = 0; i < 8; i++)
        i2s.readBytes((char *)chunk.samples, sizeof(chunk.samples));
      start_us = esp_timer_get_time();
      samples_read = 0;
      running = true;
    } else if (!mic_on && running) {
      i2s.end();
      running = false;
    }
    if (!running) {
      vTaskDelay(pdMS_TO_TICKS(20));
      continue;
    }

    chunk.bytes = i2s.readBytes((char *)chunk.samples, sizeof(chunk.samples));
    size_t n = chunk.bytes / 2;
    if (n == 0) continue;

    // Timestamp from the sample count, so audio timing stays exact
    chunk.timestamp_us = start_us + samples_read * 1000000ULL / SAMPLE_RATE;
    samples_read += n;

    // Apply gain with clipping instead of wrap-around
    for (size_t i = 0; i < n; i++) {
      int32_t v = (int32_t)chunk.samples[i] * VOLUME_GAIN;
      chunk.samples[i] = constrain(v, -32768, 32767);
    }
    xQueueSend(audio_queue, &chunk, 0);  // dropped if the queue is full
  }
}

// --- Packets ---

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

void send_frame(camera_fb_t *fb) {
  uint64_t ts = (uint64_t)fb->timestamp.tv_sec * 1000000ULL + fb->timestamp.tv_usec;
  send_packet("FRAM", ts, fb->buf, fb->len);
}

// --- Phases ---

void set_phase(Phase p, const char *cause) {
  if (p == phase) return;
  phase = p;
  Serial.printf("Mode: %s (%s)\n", PHASE_NAMES[p], cause);
  if (p == PAIRING) return;
  send_queued_audio();  // audio before the change goes out first
  char text[32];
  int len = snprintf(text, sizeof(text), "%s:%s", PHASE_NAMES[p], cause);
  send_packet("MODE", esp_timer_get_time(), (uint8_t *)text, len);
  last_snapshot_ms = millis();  // first snapshot one interval in, once the camera has settled
}

void start_capture() {
  if (phase != PAIRING) return;
  if (!camera_start()) return;
  xQueueReset(audio_queue);
  mic_on = true;
  set_phase(SNAPSHOT, "start");
}

void stop_capture() {
  mic_on = false;
  camera_stop();
  xQueueReset(audio_queue);
  set_phase(PAIRING, "disconnected");
}

void disconnect_receiver() {
  stop_capture();
  client.stop();
  Serial.println("Receiver disconnected, back to pairing");
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

void loop() {
  // A new receiver connection replaces the old one
  WiFiClient incoming = server.accept();
  if (incoming) {
    if (client.connected()) disconnect_receiver();
    client = incoming;
    client.setNoDelay(true);
    Serial.printf("Receiver connected from %s\n", client.remoteIP().toString().c_str());
  }
  if (phase != PAIRING && !client.connected()) disconnect_receiver();

  // Commands from the receiver
  while (client.available()) {
    char c = client.read();
    if (c == 'S') {
      send_packet("HELO", esp_timer_get_time(), NULL, 0);
      start_capture();
    } else if (c == 'P') {
      if (phase != PAIRING) set_phase(SNAPSHOT, "command");
    } else if (c == 'C') {
      if (phase != PAIRING) set_phase(CONTINUOUS, "command");
    } else if (c == 'X') {
      disconnect_receiver();
    }
  }

  // B button switches between snapshot and continuous (ignored while pairing)
  if (button_pressed() && phase != PAIRING)
    set_phase(phase == SNAPSHOT ? CONTINUOUS : SNAPSHOT, "button");

  if (phase == PAIRING) {
    delay(10);
    return;
  }

  // Audio goes out first, so a slow link costs frames, not sound
  send_queued_audio();
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return;
  if (phase == CONTINUOUS) {
    send_frame(fb);
  } else if (millis() - last_snapshot_ms >= SNAPSHOT_INTERVAL_MS) {
    // Snapshot mode: frames are taken all the time (the camera driver stalls for seconds
    // if frames sit unread), but only one per interval is sent
    send_frame(fb);
    last_snapshot_ms = millis();
  }
  esp_camera_fb_return(fb);
  if (phase == SNAPSHOT) delay(5);
}
