"""
Live viewer/recorder for av_stream.ino (XIAO ESP32S3 Sense).

Press B on the board to start/stop a recording. While recording, shows the
camera in a window, plays the microphone, and saves both together to a new
av_test_NNN.mkv per recording (the board's JPEG frames + 16-bit PCM audio,
synced by the board's timestamps). Plays in VLC.
Usage:  python av_receiver.py COM3
        python av_receiver.py          (lists available ports)
Press q in the video window (or Ctrl+C here) to quit.
"""
import os
import struct
import sys
import time
from fractions import Fraction

import av
import cv2
import numpy as np
import serial
import serial.tools.list_ports
import sounddevice as sd

AUDIO_MAGIC = b"AUDI"
VIDEO_MAGIC = b"FRAM"
START_MAGIC = b"STRT"           # B pressed - recording started
STOP_MAGIC = b"STOP"            # B pressed again - recording stopped
HELLO_MAGIC = b"HELO"           # board's reply to 'S'
MAGICS = (AUDIO_MAGIC, VIDEO_MAGIC, START_MAGIC, STOP_MAGIC, HELLO_MAGIC)
DATA_MAGICS = (AUDIO_MAGIC, VIDEO_MAGIC)
HEADER = struct.Struct("<QI")  # timestamp (us), payload length
MAX_PAYLOAD_BYTES = 1_000_000  # anything bigger is a corrupted length
SAMPLE_RATE = 16000
OUT_PREFIX = "av_test"
WINDOW = "XIAO camera (q to quit)"


def read_exact(ser, n):
    data = b""
    while len(data) < n:
        chunk = ser.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def read_packet(ser):
    """Find the next packet marker; return (type, timestamp_us, payload, bytes skipped before it)."""
    window = b""
    skipped = b""
    while window not in MAGICS:
        b = ser.read(1)
        if not b:
            return None, 0, None, skipped
        window = (window + b)[-4:]
        skipped += b
    skipped = skipped[:-4]
    header = read_exact(ser, HEADER.size)
    if header is None:
        return None, 0, None, skipped
    timestamp, length = HEADER.unpack(header)
    if length > MAX_PAYLOAD_BYTES or (length == 0) == (window in DATA_MAGICS):
        return None, 0, None, skipped  # data packets need a payload, control packets have none
    payload = read_exact(ser, length) if length else b""
    if payload is None:
        return None, 0, None, skipped
    return window, timestamp, payload, skipped


def print_board_text(data):
    """Show error messages the board prints (e.g. camera init failures)."""
    text = data.decode("ascii", "ignore")
    if text.strip() and all(c.isprintable() or c in "\r\n" for c in text):
        for line in text.strip().splitlines():
            print(f"Board says: {line}")


class Recorder:
    """Writes JPEG frames (copied as-is) and PCM audio into one MKV, timed by the board's clock."""

    def __init__(self, path):
        self.path = path
        self.container = None
        self.t0 = None             # board time (us) that becomes 0 in the file
        self.pending_audio = []    # audio that arrives before the first frame
        self.next_audio_pts = 0
        self.last_video_pts = -1
        self.frames = 0

    def _open(self, width, height):
        self.container = av.open(self.path, "w")
        self.video = self.container.add_stream("mjpeg")
        self.video.width = width
        self.video.height = height
        self.video.pix_fmt = "yuvj420p"
        self.video.time_base = Fraction(1, 1000)
        self.audio = self.container.add_stream("pcm_s16le", rate=SAMPLE_RATE, layout="mono")
        self.audio.time_base = Fraction(1, SAMPLE_RATE)

    def add_video(self, timestamp, jpg, width, height):
        if self.t0 is None:
            self.t0 = timestamp
        if self.container is None:
            self._open(width, height)
            for ts, pcm in self.pending_audio:
                self.add_audio(ts, pcm)
            self.pending_audio = []
        pts = (timestamp - self.t0) // 1000
        if pts <= self.last_video_pts:
            return
        packet = av.Packet(jpg)
        packet.stream = self.video
        packet.time_base = Fraction(1, 1000)
        packet.pts = packet.dts = pts
        self.container.mux(packet)
        self.last_video_pts = pts
        self.frames += 1

    def add_audio(self, timestamp, pcm):
        if self.t0 is None:
            self.t0 = timestamp
        if self.container is None:
            self.pending_audio.append((timestamp, pcm))
            return
        samples = np.frombuffer(pcm, dtype=np.int16)
        pts_from_clock = round((timestamp - self.t0) * SAMPLE_RATE / 1_000_000)
        if pts_from_clock < 0:
            return
        pts = self.next_audio_pts
        if pts_from_clock > pts + len(samples):
            pts = pts_from_clock  # board dropped audio - leave a gap so sync is kept
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = SAMPLE_RATE
        frame.time_base = Fraction(1, SAMPLE_RATE)
        frame.pts = pts
        for packet in self.audio.encode(frame):
            self.container.mux(packet)
        self.next_audio_pts = pts + len(samples)

    def close(self):
        if self.container is None:
            return False
        for packet in self.audio.encode(None):
            self.container.mux(packet)
        self.container.close()
        return True


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


def main():
    if len(sys.argv) < 2:
        print("Usage: python av_receiver.py <PORT>\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}  {p.description}")
        return

    ser = serial.Serial(sys.argv[1], 115200, timeout=0.2)
    ser.reset_input_buffer()
    ser.write(b"S")
    print(f"Connecting to {sys.argv[1]}... (Ctrl+C to quit)")

    recorder = None
    speaker = sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", latency="high")
    speaker.start()
    connected = False
    last_start_cmd = time.time()
    try:
        while True:
            kind, timestamp, payload, skipped = read_packet(ser)
            print_board_text(skipped)
            # Opening the port can reset the board and lose the first 'S', so resend until it answers
            if not connected and time.time() - last_start_cmd > 2:
                print("Waiting for the board - resending start command...")
                ser.write(b"S")
                last_start_cmd = time.time()

            if kind == HELLO_MAGIC:
                if not connected:
                    print("Connected. Press B on the board to start/stop a recording.")
                    connected = True
            elif kind == START_MAGIC:
                if recorder is not None:
                    finish_recording(recorder)
                recorder = Recorder(next_file_name())
                print(f"Recording started - saving to {recorder.path}")
            elif kind == STOP_MAGIC:
                if recorder is not None:
                    finish_recording(recorder)
                    recorder = None
            elif kind == AUDIO_MAGIC:
                speaker.write(payload)
                if recorder is not None:
                    recorder.add_audio(timestamp, payload)
            elif kind == VIDEO_MAGIC:
                img = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
                if img is not None:  # skip corrupted frames
                    cv2.imshow(WINDOW, img)
                    if recorder is not None:
                        h, w = img.shape[:2]
                        recorder.add_video(timestamp, payload, w, h)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        ser.write(b"X")
        ser.close()
        speaker.stop()
        speaker.close()
        if recorder is not None:
            finish_recording(recorder)
        cv2.destroyAllWindows()
        print("Quit.")


if __name__ == "__main__":
    main()
