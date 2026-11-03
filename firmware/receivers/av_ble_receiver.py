"""
Live viewer/recorder for av_ble.ino (XIAO ESP32S3 Sense over Bluetooth LE).

Connects to the board ("XIAO-AV") over Bluetooth, shows the camera, plays the
microphone, and saves each recording to a new av_ble_NNN.mkv (the board's JPEG
frames + 16-bit PCM audio, synced by the board's timestamps). Plays in VLC.
Start/stop a recording with the B button on the board, or r in the video window.
Usage:  python av_ble_receiver.py
        python av_ble_receiver.py --record 30   (record 30 s straight away, then quit)
Press q in the video window (or Ctrl+C here) to quit.
Needs: pip install bleak av opencv-python numpy sounddevice pyserial
"""
import argparse
import asyncio
import os
import queue
import struct
import threading
import time

import cv2
import numpy as np
import sounddevice as sd
from bleak import BleakClient, BleakScanner

from av_receiver import Recorder  # same .mkv writer as the USB version

DEVICE_NAME = "XIAO-AV"
RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # commands to the board
TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # data from the board
MAGICS = (b"AUDI", b"FRAM", b"STRT", b"STOP", b"HELO")
DATA_MAGICS = (b"AUDI", b"FRAM")
HEADER = struct.Struct("<4sQI")  # type, timestamp (us), payload length
MAX_PAYLOAD_BYTES = 1_000_000    # anything bigger is a corrupted length
SAMPLE_RATE = 16000
OUT_PREFIX = "av_ble"
WINDOW = "XIAO camera over Bluetooth (r = record, q = quit)"
DISPLAY_SCALE = 2                # 320x240 is small on screen


class BleLink:
    """Runs the Bluetooth connection in its own thread.

    Bleak needs its own thread on Windows: importing sounddevice switches the main
    thread to GUI (STA) mode, where Bleak's callbacks never arrive.
    """

    def __init__(self):
        self.received = queue.Queue()  # bytes from the board
        self.commands = queue.Queue()  # single-byte commands to the board
        self.status = queue.Queue()    # messages for the main thread
        self.alive = True
        self.thread = threading.Thread(target=lambda: asyncio.run(self._run()), daemon=True)

    def start(self):
        self.thread.start()

    def send(self, command: bytes):
        self.commands.put(command)

    def stop(self):
        self.send(b"X")
        self.alive = False
        self.thread.join(timeout=5)

    async def _run(self):
        try:
            self.status.put(f"Scanning for {DEVICE_NAME} over Bluetooth...")
            device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=20)
            if device is None:
                self.status.put("ERROR Not found - is av_ble.ino running and the board powered?")
                return
            async with BleakClient(device) as client:
                await client.start_notify(TX_UUID, lambda _, data: self.received.put(bytes(data)))
                self.status.put(f"Bluetooth connected (MTU {client.mtu_size})")
                while client.is_connected:
                    try:
                        command = self.commands.get_nowait()
                        await client.write_gatt_char(RX_UUID, command, response=True)
                        if command == b"X":
                            break
                    except queue.Empty:
                        if not self.alive:
                            break
                        await asyncio.sleep(0.01)
                else:
                    self.status.put("ERROR Bluetooth connection lost.")
        except Exception as e:
            self.status.put(f"ERROR Bluetooth: {e}")
        finally:
            self.alive = False


def parse_packets(buf: bytearray):
    """Yield (type, timestamp, payload) for each complete packet in buf and remove them."""
    pos = 0
    while len(buf) - pos >= HEADER.size:
        kind, timestamp, length = HEADER.unpack_from(buf, pos)
        valid = kind in MAGICS and length <= MAX_PAYLOAD_BYTES and (length > 0) == (kind in DATA_MAGICS)
        if not valid:
            pos += 1  # not a packet start - resync one byte later
            continue
        if len(buf) - pos < HEADER.size + length:
            break  # wait for the rest
        start = pos + HEADER.size
        yield kind, timestamp, bytes(buf[start:start + length])
        pos = start + length
    del buf[:pos]


def next_file_name():
    n = 1
    while os.path.exists(f"{OUT_PREFIX}_{n:03d}.mkv"):
        n += 1
    return f"{OUT_PREFIX}_{n:03d}.mkv"


def finish_recording(recorder):
    if recorder.close():
        print(f"Recording stopped. Saved {recorder.frames} frames + audio to {recorder.path}")
    else:
        print("Recording stopped. No frames were received, so nothing was saved.")


def main(record_seconds):
    link = BleLink()
    link.start()
    speaker = sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", latency="high")
    speaker.start()

    incoming = bytearray()
    stats = {"frames": 0, "audio": 0, "bytes": 0}
    recorder = None
    connected = False
    recording = False
    record_until = None
    last_hello = 0.0
    last_stats = time.time()
    try:
        while True:
            while not link.status.empty():
                message = link.status.get()
                print(message.removeprefix("ERROR "))
                if message.startswith("ERROR"):
                    return

            # Ask for a hello until the board answers
            if link.alive and not connected and time.time() - last_hello > 2:
                link.send(b"S")
                last_hello = time.time()

            while not link.received.empty():
                data = link.received.get()
                incoming.extend(data)
                stats["bytes"] += len(data)

            for kind, timestamp, payload in parse_packets(incoming):
                if kind == b"HELO" and not connected:
                    connected = True
                    print("Connected. Press B on the board or r in the video window to record.")
                    if record_seconds:
                        link.send(b"R")
                elif kind == b"STRT":
                    recording = True
                    record_until = time.time() + record_seconds if record_seconds else None
                    if recorder is not None:
                        finish_recording(recorder)
                    recorder = Recorder(next_file_name())
                    print(f"Recording started - saving to {recorder.path}")
                elif kind == b"STOP":
                    recording = False
                    if recorder is not None:
                        finish_recording(recorder)
                        recorder = None
                    if record_seconds:
                        return
                elif kind == b"AUDI":
                    stats["audio"] += 1
                    speaker.write(payload)
                    if recorder is not None:
                        recorder.add_audio(timestamp, payload)
                elif kind == b"FRAM":
                    img = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:  # skip corrupted frames
                        stats["frames"] += 1
                        h, w = img.shape[:2]
                        cv2.imshow(WINDOW, cv2.resize(img, (w * DISPLAY_SCALE, h * DISPLAY_SCALE)))
                        if recorder is not None:
                            recorder.add_video(timestamp, payload, w, h)

            if time.time() - last_stats >= 1:
                if recording:
                    print(f"{stats['frames']} fps, {stats['audio']} audio packets/s, {stats['bytes'] / 1024:.0f} KB/s")
                stats.update(frames=0, audio=0, bytes=0)
                last_stats = time.time()

            if record_until and recording and time.time() > record_until:
                link.send(b"E")
                record_until = None

            key = cv2.waitKey(5) & 0xFF
            if key == ord("q"):
                return
            if key == ord("r") and connected:
                link.send(b"E" if recording else b"R")
    except KeyboardInterrupt:
        pass
    finally:
        link.stop()
        speaker.stop()
        speaker.close()
        if recorder is not None:
            finish_recording(recorder)
        cv2.destroyAllWindows()
        print("Quit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live viewer/recorder for av_ble.ino")
    parser.add_argument("--record", type=float, metavar="SECONDS",
                        help="start a recording straight away, stop after SECONDS, then quit")
    main(parser.parse_args().record)
