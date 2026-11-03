/*
 * BLE throughput test for Seeed XIAO ESP32S3 (Sense)
 * Advertises as "XIAO-BLE-TEST" and, once a central subscribes to the data
 * characteristic, sends numbered notifications as fast as the link accepts them.
 * Each notification: 4-byte little-endian sequence number + filler, sized to
 * the negotiated MTU. When the BLE send buffers are full, notify() fails and
 * the same packet is retried, so the accepted rate equals the link's real rate.
 * Prints the send rate once per second over USB serial. Pair with
 * ble_throughput_pc.py (or any BLE app that subscribes to notifications).
*/

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include "host/ble_gap.h"

#define DEVICE_NAME  "XIAO-BLE-TEST"
#define SERVICE_UUID "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define DATA_UUID    "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

BLEServer *server;
BLECharacteristic *data_char;
volatile bool subscribed = false;
volatile bool send_failed = false;
volatile uint16_t conn_handle = 0;
volatile uint16_t mtu = 23;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *s, ble_gap_conn_desc *desc) override {
    conn_handle = desc->conn_handle;
    Serial.printf("Connected, interval %.2f ms\n", desc->conn_itvl * 1.25);
    // Ask for the fastest settings: 7.5-15 ms connection interval, 2M PHY, 251-byte link packets
    s->updateConnParams(desc->conn_handle, 6, 12, 0, 400);
    int phy_rc = ble_gap_set_prefered_le_phy(desc->conn_handle, BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, 0);
    int dle_rc = ble_gap_set_data_len(desc->conn_handle, 251, 2120);
    Serial.printf("Requested 2M PHY (rc=%d) and 251-byte packets (rc=%d)\n", phy_rc, dle_rc);
  }
  void onDisconnect(BLEServer *s, ble_gap_conn_desc *desc) override {
    subscribed = false;
    Serial.println("Disconnected - advertising again");
    BLEDevice::startAdvertising();
  }
  void onMtuChanged(BLEServer *s, ble_gap_conn_desc *desc, uint16_t new_mtu) override {
    mtu = new_mtu;
    Serial.printf("MTU %u (notification payload %u bytes)\n", new_mtu, new_mtu - 3);
  }
};

class DataCallbacks : public BLECharacteristicCallbacks {
  void onSubscribe(BLECharacteristic *c, ble_gap_conn_desc *desc, uint16_t sub_value) override {
    subscribed = sub_value & 1;
    Serial.println(subscribed ? "Subscribed - sending" : "Unsubscribed");
  }
  void onStatus(BLECharacteristic *c, Status s, uint32_t code) override {
    if (s == ERROR_GATT) send_failed = true;  // send buffers full - retry this packet
  }
};

void setup() {
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);  // never block when no serial monitor is reading

  BLEDevice::init(DEVICE_NAME);
  BLEDevice::setMTU(517);
  server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService *service = server->createService(SERVICE_UUID);
  data_char = service->createCharacteristic(DATA_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  data_char->addDescriptor(new BLE2902());
  data_char->setCallbacks(new DataCallbacks());
  service->start();
  BLEDevice::getAdvertising()->addServiceUUID(SERVICE_UUID);
  BLEDevice::startAdvertising();
  Serial.println("Advertising as " DEVICE_NAME);
}

void loop() {
  static uint8_t packet[512];
  static uint32_t seq = 0, bytes = 0, packets = 0, retries = 0, last_report = 0;

  if (!subscribed) {
    seq = bytes = packets = retries = 0;
    last_report = millis();
    delay(50);
    return;
  }

  size_t size = min<size_t>(mtu - 3, sizeof(packet));
  memcpy(packet, &seq, 4);
  data_char->setValue(packet, size);
  send_failed = false;
  data_char->notify();
  if (send_failed) {
    retries++;
    delay(1);  // let the radio drain the buffers, then resend the same packet
  } else {
    seq++;
    packets++;
    bytes += size;
  }

  if (millis() - last_report >= 1000) {
    Serial.printf("sent %.1f KB/s (%u packets of %u bytes, %u retries)\n", bytes / 1024.0, packets, size, retries);
    bytes = packets = retries = 0;
    last_report = millis();
  }
}
