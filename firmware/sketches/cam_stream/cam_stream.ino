/*
 * Live camera stream for Seeed XIAO ESP32S3 Sense
 * Sends JPEG frames over the USB cable, each prefixed with
 * "FRAM" + 4-byte little-endian length.
 * Run cam_receiver.py on the computer to view and save a video.
 * The board starts sending on 'S' and stops on 'X'.
 * Requires ESP32 Arduino core 3.x with PSRAM set to "OPI PSRAM".
*/

#include "esp_camera.h"

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

// make changes as needed
#define FRAME_SIZE   FRAMESIZE_VGA  // 640x480; try QVGA for more fps, SVGA/HD for more detail
#define JPEG_QUALITY 12             // 0-63, lower = better quality but bigger frames

const uint8_t FRAME_MAGIC[4] = {'F', 'R', 'A', 'M'};
bool streaming = false;

void setup() {
  Serial.begin(115200);

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
  if (err != ESP_OK) {
    while (1) {
      Serial.printf("Camera init failed: 0x%x\n", err);
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
  if (!streaming) {
    delay(10);
    return;
  }

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return;

  // Binary frames only - no text may be printed while streaming
  uint32_t len = fb->len;
  Serial.write(FRAME_MAGIC, 4);
  Serial.write((uint8_t *)&len, 4);
  Serial.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}
