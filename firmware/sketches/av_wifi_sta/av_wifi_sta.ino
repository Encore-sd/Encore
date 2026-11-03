/*
 * WiFi audio + video stream for Seeed XIAO ESP32S3 Sense - joins your WiFi
 * Fork of av_wifi.ino: instead of always making its own network, the board joins
 * a WiFi network you give it over Bluetooth (the av_app_sta app), so the phone
 * keeps its normal internet. Listens for one app on TCP port 5000 there, and
 * announces itself as xiao-av.local. If no network is saved, or the saved one
 * can't be joined at power-up, it falls back to its own network (AP_SSID /
 * AP_PASSWORD) at 192.168.4.1 like av_wifi.ino.
 * Bluetooth setup ("XIAO-AV", SETUP_SERVICE_UUID): write "ssid\npassword" to
 * CREDS_UUID (empty = forget the network); STATUS_UUID (read/notify) reports
 * "connected <ip> <ssid>", "connecting <ssid>" or "ap 192.168.4.1 [reason]".
 * Writing to SCAN_UUID scans for WiFi networks; reading it gives "scanning", then
 * one "rssi\tsecured(0/1)\tssid" line per network, strongest first.
 * Bluetooth only runs while the board has no working network (setup mode): it
 * never starts if the saved network is joined at power-up, and turns off once
 * setup succeeds and the app disconnects, because WiFi only runs at full speed
 * (~2x the frame rate) with Bluetooth off.
 * To change networks: forget the saved one (app 'F' command, or hold B for
 * FORGET_HOLD_MS), which restarts the board in setup mode.
 * Packets are the same as av_stream.ino:
 *   4-byte type + 8-byte timestamp (us since boot) + 4-byte length + data,
 *   all little-endian. Types: "AUDI" audio, "FRAM" JPEG frame,
 *   "STRT"/"STOP" recording started/stopped, "HELO" reply to 'S'.
 * Commands from the app (single characters):
 *   'S' hello, 'R' start recording, 'E' end recording, 'X' disconnecting,
 *   'F' forget the saved WiFi and restart in setup mode.
 * A short press of the B (BOOT) button starts/stops a recording once an app is
 * connected; holding it for FORGET_HOLD_MS forgets the saved WiFi.
 * Orange LED: slow flash = setup mode (own network, nothing joined);
 * solid = on a WiFi network (or a device joined ours); fast flash = recording.
 * Quick flashes: 4 = joined the WiFi network, 2 = an app connected.
 * Slow flashes: 2 = app disconnected, 4 = forgetting the WiFi (then restarts).
 * Status messages go to USB serial.
 * Requires ESP32 Arduino core 3.x with PSRAM set to "OPI PSRAM",
 * and the WiFi antenna attached.
*/

#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
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
#define AP_SSID      "XIAO-AV"      // fallback network, also the Bluetooth name
#define AP_PASSWORD  "xiaoav123"    // at least 8 characters
#define HOSTNAME     "xiao-av"      // reachable as xiao-av.local on a joined network
#define TCP_PORT     5000
#define JOIN_TIMEOUT_MS 15000       // give up joining the saved network after this
#define FORGET_HOLD_MS  3000        // hold B this long to forget the saved WiFi
#define VOLUME_GAIN  1              // multiplier, 1 = raw mic signal
#define FRAME_SIZE   FRAMESIZE_VGA  // 640x480; try QVGA for more fps, SVGA/HD for more detail
#define JPEG_QUALITY 12             // 0-63, lower = better quality but bigger frames
#define LED_BLINK_MS 250            // LED on/off time while recording
#define LED_WAIT_MS  1000           // LED on/off time while waiting for a device to join
#define LED_FLASH_MS 100            // LED on/off time of the quick confirmation flashes
#define LED_SLOW_FLASH_MS 300       // ...and of the slower ones for disconnecting/forgetting

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
volatile bool device_joined = false;  // LED solid: on a WiFi network / a device joined ours
volatile uint32_t flash_start_ms = 0, flash_end_ms = 0, flash_period_ms = LED_FLASH_MS;  // confirmation flashes

// Bluetooth WiFi setup
#define SETUP_SERVICE_UUID "7a1e0001-3c4f-4a4b-9d2e-5f6a7b8c9d00"
#define CREDS_UUID         "7a1e0002-3c4f-4a4b-9d2e-5f6a7b8c9d00"
#define STATUS_UUID        "7a1e0003-3c4f-4a4b-9d2e-5f6a7b8c9d00"
#define SCAN_UUID          "7a1e0004-3c4f-4a4b-9d2e-5f6a7b8c9d00"
#define SCAN_LIST_MAX      500     // bytes; a Bluetooth read returns at most 512
Preferences prefs;
BLECharacteristic *status_char;
BLECharacteristic *scan_char;
volatile bool scan_pending = false;
bool ble_on = false;
bool ble_used = false;              // Bluetooth can't be restarted once turned off (until reboot)
volatile int ble_clients = 0;
volatile bool creds_pending = false;
String pending_creds;               // "ssid\0password" written over Bluetooth
bool ap_mode = false;
String sta_ssid;
String ap_note;                     // why we're on our own network
String last_status;

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

  // Join the saved network, or fall back to our own (which also starts Bluetooth setup)
  prefs.begin("wifi", false);
  String ssid = prefs.getString("ssid", "");
  if (ssid.length()) join_network(ssid, prefs.getString("pass", ""));
  else start_own_network("not set up");
  server.begin();
  server.setNoDelay(true);

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
    uint32_t ms = millis();
    if (ms < flash_end_ms) led_on = ((ms - flash_start_ms) / flash_period_ms) % 2 == 0;
    else if (recording) led_on = (now_ms / LED_BLINK_MS) % 2 == 0;
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

// True once per short press of the B button (on release), ignoring contact bounce.
// Holding it for FORGET_HOLD_MS forgets the saved WiFi instead.
bool button_pressed() {
  static bool was_down = false;
  static uint32_t last_change = 0, down_since = 0;
  bool down = digitalRead(BUTTON_PIN) == LOW;
  if (down != was_down && millis() - last_change > 50) {
    was_down = down;
    last_change = millis();
    if (down) down_since = millis();
    else return millis() - down_since < FORGET_HOLD_MS;
  }
  if (was_down && millis() - down_since >= FORGET_HOLD_MS) forget_network();
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

// LED flashes as a confirmation, then back to the normal pattern. Returns their duration.
uint32_t flash_led(int times, uint32_t period_ms = LED_FLASH_MS) {
  flash_period_ms = period_ms;
  flash_start_ms = millis();
  flash_end_ms = flash_start_ms + times * 2 * period_ms;
  return times * 2 * period_ms;
}

// --- Network: join the saved WiFi, or fall back to our own ---

String current_status() {
  if (ap_mode) return "ap " + WiFi.softAPIP().toString() + (ap_note.length() ? " " + ap_note : "");
  if (WiFi.status() == WL_CONNECTED) return "connected " + WiFi.localIP().toString() + " " + sta_ssid;
  return "connecting " + sta_ssid;
}

// Publishes the status over Bluetooth (and serial) when it changes
void update_status() {
  String status = current_status();
  if (status == last_status) return;
  last_status = status;
  Serial.println("Status: " + status);
  if (ble_on) {
    status_char->setValue(status.c_str());
    if (ble_clients) status_char->notify();
  }
}

void start_own_network(const String &note) {
  MDNS.end();
  ap_mode = true;
  ap_note = note;
  if (!ble_on && !ble_used) start_ble_setup();  // so the WiFi can be set up
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP(AP_SSID, AP_PASSWORD)) fail("Failed to start WiFi network", 0);
  WiFi.setSleep(false);  // power saving off because it adds long send delays
  Serial.printf("WiFi network \"%s\" ready (%s), app connects to %s:%d\n",
                AP_SSID, note.c_str(), WiFi.softAPIP().toString().c_str(), TCP_PORT);
  update_status();
}

// Joins ssid, falling back to our own network if that fails. Blocks up to JOIN_TIMEOUT_MS.
bool join_network(const String &ssid, const String &pass) {
  if (client.connected()) disconnect_app();
  MDNS.end();
  WiFi.softAPdisconnect(true);
  ap_mode = false;
  sta_ssid = ssid;
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  WiFi.begin(ssid.c_str(), pass.c_str());
  update_status();  // "connecting <ssid>"
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < JOIN_TIMEOUT_MS) delay(100);

  if (WiFi.status() == WL_CONNECTED) {
    MDNS.begin(HOSTNAME);
    MDNS.addService("xiaoav", "tcp", TCP_PORT);
    Serial.printf("Joined \"%s\", app connects to %s:%d (%s.local)\n",
                  ssid.c_str(), WiFi.localIP().toString().c_str(), TCP_PORT, HOSTNAME);
    WiFi.setSleep(false);  // fails while Bluetooth is on; set again when it turns off
    flash_led(4);  // joined the network
    update_status();
    return true;
  }
  String reason = WiFi.status() == WL_NO_SSID_AVAIL ? "network not found" : "could not connect - check the password";
  WiFi.disconnect(true);
  start_own_network("could not join " + ssid + ": " + reason);
  return false;
}

// --- Bluetooth WiFi setup ---

class SetupServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *server, ble_gap_conn_desc *desc) override {
    ble_clients++;
  }
  void onDisconnect(BLEServer *server, ble_gap_conn_desc *desc) override {
    ble_clients--;
    BLEDevice::startAdvertising();
  }
};

class CredsCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    pending_creds = c->getValue();  // handled in loop(), joining blocks for a while
    creds_pending = true;
  }
};

class ScanCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    c->setValue("scanning");  // until loop() has the results
    scan_pending = true;
  }
};

// Scans for WiFi networks and publishes them on SCAN_UUID: one "rssi\tsecured\tssid"
// line per network, strongest first, with duplicates and hidden networks left out
void scan_networks() {
  scan_pending = false;
  Serial.println("Scanning for WiFi networks...");
  int n = WiFi.scanNetworks();  // ~2-4 s; also works while running our own network
  int order[n > 0 ? n : 1];
  for (int i = 0; i < n; i++) order[i] = i;
  for (int i = 0; i < n; i++)  // strongest signal first
    for (int j = i + 1; j < n; j++)
      if (WiFi.RSSI(order[j]) > WiFi.RSSI(order[i])) std::swap(order[i], order[j]);

  String list, seen = "\n";
  for (int k = 0; k < n; k++) {
    int i = order[k];
    String ssid = WiFi.SSID(i);
    if (!ssid.length() || seen.indexOf("\n" + ssid + "\n") >= 0) continue;
    seen += ssid + "\n";
    String line = String(WiFi.RSSI(i)) + "\t" + (WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "0" : "1") + "\t" + ssid + "\n";
    if (list.length() + line.length() > SCAN_LIST_MAX) break;
    list += line;
  }
  WiFi.scanDelete();
  scan_char->setValue(list.c_str());
  Serial.printf("Found %d networks\n", n);
}

void start_ble_setup() {
  BLEDevice::init(AP_SSID);
  BLEServer *ble_server = BLEDevice::createServer();
  ble_server->setCallbacks(new SetupServerCallbacks());
  BLEService *service = ble_server->createService(SETUP_SERVICE_UUID);
  BLECharacteristic *creds = service->createCharacteristic(CREDS_UUID, BLECharacteristic::PROPERTY_WRITE);
  creds->setCallbacks(new CredsCallbacks());
  status_char = service->createCharacteristic(
    STATUS_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  status_char->addDescriptor(new BLE2902());
  scan_char = service->createCharacteristic(
    SCAN_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  scan_char->setCallbacks(new ScanCallbacks());
  service->start();
  BLEDevice::getAdvertising()->addServiceUUID(SETUP_SERVICE_UUID);
  BLEDevice::startAdvertising();
  ble_on = ble_used = true;
  Serial.println("Bluetooth setup on");
}

// Bluetooth off until the next restart: WiFi only runs at full speed without it
void stop_ble_setup() {
  BLEDevice::deinit(true);
  ble_on = false;
  WiFi.setSleep(false);  // power saving off because it adds long send delays
  Serial.println("Bluetooth setup off");
}

// Clears the saved WiFi and restarts in setup mode (own network + Bluetooth)
void forget_network() {
  Serial.println("Forgetting the saved WiFi - restarting in setup mode");
  prefs.remove("ssid");
  prefs.remove("pass");
  if (client.connected()) disconnect_app();
  delay(flash_led(4, LED_SLOW_FLASH_MS));  // show the flashes before restarting
  ESP.restart();
}

// Applies WiFi details written over Bluetooth: "ssid\npassword", empty = forget
void apply_pending_creds() {
  creds_pending = false;
  String value = pending_creds;
  int newline = value.indexOf('\n');
  String ssid = newline < 0 ? value : value.substring(0, newline);
  String pass = newline < 0 ? "" : value.substring(newline + 1);
  if (ssid.length()) {
    prefs.putString("ssid", ssid);
    prefs.putString("pass", pass);
    join_network(ssid, pass);
  } else {
    prefs.remove("ssid");
    prefs.remove("pass");
    if (client.connected()) disconnect_app();
    WiFi.disconnect(true);
    start_own_network("not set up");
  }
}

void loop() {
  // WiFi setup over Bluetooth
  if (scan_pending) scan_networks();
  if (creds_pending) apply_pending_creds();
  update_status();
  // Setup done: Bluetooth off once the app has read the result and disconnected
  if (ble_on && !ap_mode && WiFi.status() == WL_CONNECTED && ble_clients == 0) stop_ble_setup();

  // LED solid: on a WiFi network, or a device joined our own network
  bool joined = ap_mode ? WiFi.softAPgetStationNum() > 0 : WiFi.status() == WL_CONNECTED;
  if (joined != device_joined) {
    device_joined = joined;
    if (ap_mode) Serial.println(joined ? "Device joined our network" : "No devices on our network");
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
      flash_led(2);  // app connected
    } else if (c == 'R') {
      if (receiver_ready && !recording) start_recording();
    } else if (c == 'E') {
      stop_recording(true);
    } else if (c == 'X') {
      disconnect_app();
      flash_led(2, LED_SLOW_FLASH_MS);  // app disconnected
    } else if (c == 'F') {
      forget_network();
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
