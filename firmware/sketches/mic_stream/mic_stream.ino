/*
 * Live microphone stream for Seeed XIAO ESP32S3 Sense
 * Sends raw 16 kHz, 16-bit, mono PCM over the USB cable.
 * Run mic_receiver.py on the computer to listen and save a WAV.
 * The board starts sending on 'S' and stops on 'X'.
 * Requires ESP32 Arduino core 3.x (ESP_I2S library).
*/

#include <ESP_I2S.h>

// do not change for best
#define SAMPLE_RATE 16000U

// make changes as needed
#define VOLUME_GAIN 1     // multiplier, 1 = raw mic signal
#define CHUNK_BYTES 1024  // 512 samples = 32 ms of audio per chunk

I2SClass i2s;
int16_t chunk[CHUNK_BYTES / 2];
bool streaming = false;

void setup() {
  Serial.begin(115200);
  i2s.setPinsPdmRx(42, 41);  // PDM clock, PDM data
  if (!i2s.begin(I2S_MODE_PDM_RX, SAMPLE_RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO)) {
    while (1) {
      Serial.println("Failed to initialize I2S!");
      delay(1000);
    }
  }
}

void loop() {
  // Start/stop commands from the computer
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'S') streaming = true;
    else if (c == 'X') streaming = false;
  }
  if (!Serial) streaming = false;

  // Always read the mic so old audio doesn't pile up while idle
  size_t bytes_read = i2s.readBytes((char *)chunk, CHUNK_BYTES);
  if (!streaming || bytes_read == 0) return;

  // Apply gain with clipping instead of wrap-around
  size_t samples = bytes_read / 2;
  for (size_t i = 0; i < samples; i++) {
    int32_t v = (int32_t)chunk[i] * VOLUME_GAIN;
    chunk[i] = constrain(v, -32768, 32767);
  }

  // Raw binary only - no text may be printed while streaming
  Serial.write((uint8_t *)chunk, samples * 2);
}
