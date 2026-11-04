/*
 * WiFi throughput test for Seeed XIAO ESP32S3 (Sense)
 * Joins the WiFi network saved by av_wifi_sta.ino (read from its "wifi"
 * preferences, never changed) and, once a PC connects to TCP port 5001,
 * sends numbered 8 KB blocks as fast as the link accepts them.
 * Each block: 4-byte little-endian sequence number + filler.
 * Prints the send rate once per second over USB serial. Pair with
 * wifi_throughput_pc.py. Set WITH_BLE to 1 to keep Bluetooth advertising
 * during the test, like av_wifi_sta.ino does in setup mode. Set USE_AP to 1
 * to make its own network instead (AP_SSID, at 192.168.4.1), like av_wifi.ino.
*/

#include <WiFi.h>
#include <Preferences.h>

#define WITH_BLE   0
#define USE_AP     1
#define AP_SSID     "XIAO-AV-TEST"
#define AP_PASSWORD "xiaoav123"
#define TCP_PORT   5001
#define BLOCK_SIZE 8192

#if WITH_BLE
#include <BLEDevice.h>
#endif

WiFiServer server(TCP_PORT);
uint8_t block[BLOCK_SIZE];

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);
  delay(1000);

  Preferences prefs;
  prefs.begin("wifi", true);  // read-only
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  prefs.end();
  while (!ssid.length()) {
    Serial.println("No saved WiFi - set it up with av_wifi_sta.ino first");
    delay(2000);
  }

#if WITH_BLE
  BLEDevice::init("XIAO-WIFI-TEST");
  BLEDevice::getAdvertising()->addServiceUUID("7a1e0001-3c4f-4a4b-9d2e-5f6a7b8c9d00");
  BLEDevice::startAdvertising();
  Serial.println("Bluetooth advertising during the test");
#endif

#if USE_AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);
  WiFi.setSleep(false);
  server.begin();
  server.setNoDelay(true);
  for (int i = 0; i < 3; i++) {
    Serial.printf("Own network \"%s\" (channel %d), test server at %s:%d\n",
                  AP_SSID, WiFi.channel(), WiFi.softAPIP().toString().c_str(), TCP_PORT);
    delay(1000);
  }
#else
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(), pass.c_str());
  while (WiFi.status() != WL_CONNECTED) delay(100);
  WiFi.setSleep(false);  // fails while Bluetooth is on
  server.begin();
  server.setNoDelay(true);
  for (int i = 0; i < 3; i++) {  // repeated in case the serial monitor opened late
    Serial.printf("Joined \"%s\" (RSSI %d dBm, channel %d), test server at %s:%d\n",
                  ssid.c_str(), WiFi.RSSI(), WiFi.channel(), WiFi.localIP().toString().c_str(), TCP_PORT);
    delay(1000);
  }
#endif
}

void loop() {
  WiFiClient client = server.accept();
  if (!client) {
    delay(10);
    return;
  }
  client.setNoDelay(true);
  Serial.printf("PC connected from %s\n", client.remoteIP().toString().c_str());

  uint32_t seq = 0, sent = 0, last = millis();
  while (client.connected()) {
    memcpy(block, &seq, 4);
    size_t n = client.write(block, sizeof(block));
    if (n == 0) break;
    seq++;
    sent += n;
    if (millis() - last >= 1000) {
      Serial.printf("sent %6.1f KB/s (RSSI %d dBm)\n", sent / 1024.0 * 1000 / (millis() - last), WiFi.RSSI());
      sent = 0;
      last = millis();
    }
  }
  client.stop();
  Serial.println("PC disconnected");
}
