folder for managing contents of hardware code

Firmware and test tools for the Encore wearable prototype: a Seeed XIAO ESP32-S3 Sense streaming microphone audio and camera images to a phone or PC.

## Layout

| Folder | Contents |
| --- | --- |
| `sketches/` | Arduino firmware, one folder per sketch |
| `receivers/` | PC receivers that view, play and record the streams |
| `tests/` | Throughput tests and measurement scripts |
| `test_apps/` | Android test apps (Expo SDK 58) for the WiFi firmware |

## Sketches

| Sketch | Link | Receiver |
| --- | --- | --- |
| `mic_stream` | USB serial, audio only | `receivers/mic_receiver.py` |
| `cam_stream` | USB serial, images only | `receivers/cam_receiver.py` |
| `av_stream` | USB serial, audio + images | `receivers/av_receiver.py` |
| `av_wifi` | Board's own WiFi network `XIAO-AV` at 192.168.4.1:5000 | `test_apps/av_app` |
| `av_wifi_fast` | As `av_wifi`, smaller JPEGs (quality 25) | `test_apps/av_app` |
| `av_wifi_sta` | Joins an existing WiFi network, set up over Bluetooth; falls back to its own network | `test_apps/av_app_sta` |
| `av_ble` | Bluetooth LE | `receivers/av_ble_receiver.py` |
| `av_wifi_audio` | As `av_wifi`, audio only (camera never started) | `tests/stream_rate_audio_only.py` |
| `av_wifi_sim` | Simulated capture cycle on the board's own network: pairing (camera and mic off), then snapshot mode (audio + one frame every 1.5 s), switched to and from continuous mode with B or by the receiver | `receivers/sim_receiver.py` |

Board settings: ESP32 Arduino core 3.x, board "XIAO_ESP32S3", PSRAM "OPI PSRAM", antenna attached.

All streaming sketches send the same packets: a 4-byte type (`AUDI`, `FRAM`, `STRT`, `STOP`, `HELO`), an 8-byte timestamp in microseconds since boot, a 4-byte data length (all little-endian), then the data. Commands to the board are single characters: `S` hello, `R` record, `E` end, `X` disconnect (`F` forget the saved network on `av_wifi_sta`). `av_wifi_sim` adds a `MODE` packet (text data, `snapshot:button` and similar) sent whenever the capture mode changes, and the commands `P` (snapshot mode) and `C` (continuous mode).

## PC dependencies

```
pip install pyserial sounddevice opencv-python numpy av bleak
```

Run `receivers/av_ble_receiver.py` and `receivers/sim_receiver.py` from the `receivers/` folder: they import the recorder from `av_receiver.py`.

## Tests

| Test | Board | PC |
| --- | --- | --- |
| Bluetooth LE raw capacity | `tests/ble_throughput_test` | `ble_throughput_pc.py` |
| WiFi raw capacity (`WITH_BLE`, `USE_AP` switches) | `tests/wifi_throughput_test` (station mode uses the network saved by `av_wifi_sta`) | `wifi_throughput_pc.py HOST` |
| Real WiFi stream rate | `av_wifi` or `av_wifi_sta` | `stream_rate.py HOST` |
| Real WiFi stream rate, audio only | `av_wifi_audio` | `stream_rate_audio_only.py HOST` |
| Real Bluetooth stream rate | `av_ble` | `ble_stream_rate.py` |

`serial_log.py` logs the board's USB serial to a file. `on_board_network.ps1` (Windows) joins the board's own network for one test and then rejoins the home network; it cuts the PC's internet while it runs.

## Test apps

Both apps need a development build, not Expo Go, because they use native modules (`react-native-tcp-socket`, `react-native-ble-plx`, and a native JPEG preview). See each app's README.
