"""
Live viewer for cam_stream.ino (XIAO ESP32S3 Sense).

Shows the board's camera in a window and saves it to cam_test.avi.
Usage:  python cam_receiver.py COM5
        python cam_receiver.py          (lists available ports)
Press q in the video window (or Ctrl+C) to stop.
"""
import struct
import sys
import time

import cv2
import numpy as np
import serial
import serial.tools.list_ports

MAGIC = b"FRAM"
MAX_FRAME_BYTES = 1_000_000  # anything bigger is a corrupted length
OUT_FILE = "cam_test.avi"
FPS_PROBE_SECONDS = 2        # measure frame rate before creating the video file
WINDOW = "XIAO camera (q to quit)"


def read_exact(ser, n):
    data = b""
    while len(data) < n:
        chunk = ser.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def read_frame(ser):
    """Find the next "FRAM" marker and return (JPEG or None, bytes skipped before it)."""
    window = b""
    skipped = b""
    while window != MAGIC:
        b = ser.read(1)
        if not b:
            return None, skipped
        window = (window + b)[-4:]
        skipped += b
    skipped = skipped[:-4]
    header = read_exact(ser, 4)
    if header is None:
        return None, skipped
    (length,) = struct.unpack("<I", header)
    if length == 0 or length > MAX_FRAME_BYTES:
        return None, skipped
    return read_exact(ser, length), skipped


def print_board_text(data):
    """Show error messages the board prints (e.g. camera init failures)."""
    text = data.decode("ascii", "ignore")
    if text.strip() and all(c.isprintable() or c in "\r\n" for c in text):
        for line in text.strip().splitlines():
            print(f"Board says: {line}")


def open_writer(frames, elapsed):
    fps = max(1.0, len(frames) / max(elapsed, 0.001))
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(OUT_FILE, cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    for f in frames:
        writer.write(f)
    print(f"~{fps:.1f} fps at {w}x{h} - saving to {OUT_FILE}")
    return writer


def main():
    if len(sys.argv) < 2:
        print("Usage: python cam_receiver.py <PORT>\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}  {p.description}")
        return

    ser = serial.Serial(sys.argv[1], 115200, timeout=1)
    ser.reset_input_buffer()
    ser.write(b"S")
    print(f"Connecting to {sys.argv[1]}. Press q in the video window (or Ctrl+C here) to stop.")

    writer = None
    probe = []
    start = None
    got_frame = False
    last_start_cmd = time.time()
    try:
        while True:
            jpg, skipped = read_frame(ser)
            print_board_text(skipped)
            # Opening the port can reset the board and lose the first 'S', so resend until frames arrive
            if not got_frame and time.time() - last_start_cmd > 2:
                print("No frames received yet - resending start command...")
                ser.write(b"S")
                last_start_cmd = time.time()
            img = None
            if jpg is not None:
                img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)

            if img is not None:  # skip corrupted frames
                if not got_frame:
                    print("Receiving frames - video window opened.")
                    got_frame = True
                cv2.imshow(WINDOW, img)
                if writer is not None:
                    writer.write(img)
                else:
                    if start is None:
                        start = time.time()
                    probe.append(img)
                    if time.time() - start >= FPS_PROBE_SECONDS:
                        writer = open_writer(probe, time.time() - start)
                        probe = []

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        ser.write(b"X")
        ser.close()
        if writer is None and probe:
            writer = open_writer(probe, time.time() - start)
        if writer is not None:
            writer.release()
            print(f"Stopped. Video saved to {OUT_FILE}")
        else:
            print("Stopped. No frames were received, so no video was saved.")
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
