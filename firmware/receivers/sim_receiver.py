"""
Receiver for av_wifi_sim.ino: captures the stream, follows the board's capture modes and
switches them.

Connects to the board, which then starts in snapshot mode (continuous audio, one frame every
1.5 s). Prints the mode and the stream rate each second, and a line whenever the mode
changes, whether from the B button or from this script. Saves the stream as an .mkv
(JPEG frames + 16-bit PCM audio, on the board's clock; plays in VLC) and a CSV of the mode
changes.

Keys while it runs:
  p  snapshot mode      c  continuous mode      m  switch modes      q  quit

Usage:
  py sim_receiver.py                        # board at 192.168.4.1, run until q
  py sim_receiver.py --seconds 120          # stop after 2 minutes
  py sim_receiver.py --no-save              # don't write files
Join the board's network ("XIAO-AV", password xiaoav123) first.
Run from the receivers folder: it uses the recorder in av_receiver.py.
"""
import argparse
import csv
import os
import queue
import socket
import struct
import sys
import threading
import time

from av_receiver import Recorder  # same .mkv writer as the USB version

HEADER = struct.Struct("<4sQI")  # type, timestamp (us), payload length
TYPES = {b"AUDI", b"FRAM", b"HELO", b"MODE"}
MAX_PAYLOAD_BYTES = 1_000_000    # anything bigger is a corrupted length
KEYS = {"p": b"P", "c": b"C"}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="192.168.4.1")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--seconds", type=float, default=0, help="stop after this long (default: until q)")
    p.add_argument("--no-save", action="store_true", help="don't write the .mkv and mode log")
    p.add_argument("--prefix", default="sim", help="file name prefix (default sim -> sim_001.mkv)")
    return p.parse_args()


def next_name(prefix):
    n = 1
    while os.path.exists(f"{prefix}_{n:03d}.mkv") or os.path.exists(f"{prefix}_{n:03d}_modes.csv"):
        n += 1
    return f"{prefix}_{n:03d}"


def jpeg_size(jpg):
    """(width, height) from a JPEG's start-of-frame marker, or None."""
    pos = 2
    while pos + 9 < len(jpg) and jpg[pos] == 0xFF:
        marker = jpg[pos + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            return int.from_bytes(jpg[pos + 7:pos + 9], "big"), int.from_bytes(jpg[pos + 5:pos + 7], "big")
        pos += 2 + int.from_bytes(jpg[pos + 2:pos + 4], "big")
    return None


def key_reader(keys):
    """Puts single key presses on the queue (Windows: no Enter needed; elsewhere: key + Enter)."""
    try:
        import msvcrt
        while True:
            keys.put(msvcrt.getwch().lower())
    except ImportError:
        for line in sys.stdin:
            for ch in line.strip().lower():
                keys.put(ch)


def parse_packets(buf):
    """Yield (type, timestamp, payload) for each complete packet in buf and remove them."""
    pos = 0
    while len(buf) - pos >= HEADER.size:
        kind, ts, length = HEADER.unpack_from(buf, pos)
        if kind not in TYPES or length > MAX_PAYLOAD_BYTES:
            pos += 1  # not a packet start - resync one byte later
            continue
        if len(buf) - pos < HEADER.size + length:
            break  # wait for the rest
        start = pos + HEADER.size
        yield kind, ts, bytes(buf[start:start + length])
        pos = start + length
    del buf[:pos]


def main():
    args = parse_args()
    s = socket.create_connection((args.host, args.port), timeout=5)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.settimeout(0.05)
    s.sendall(b"S")

    name = None if args.no_save else next_name(args.prefix)
    recorder = None if args.no_save else Recorder(f"{name}.mkv")
    keys = queue.Queue()
    threading.Thread(target=key_reader, args=(keys,), daemon=True).start()
    print(f"Connected to {args.host}:{args.port}. Keys: p = snapshot, c = continuous, m = switch, q = quit")

    buf = bytearray()
    mode, mode_since = None, time.time()
    changes = []                 # (seconds since start, board seconds, mode, cause)
    per_mode = {}                # mode -> {"seconds", "frames", "audio", "bytes"}, counted as packets arrive
    sec = {"bytes": 0, "frames": 0, "audio": 0}
    switched = False             # the mode changed during this second
    start = last = time.time()
    board_t0 = None

    def count(key, n=1):
        if mode:
            per_mode.setdefault(mode, {"seconds": 0, "frames": 0, "audio": 0, "bytes": 0})[key] += n
    try:
        while not args.seconds or time.time() - start < args.seconds:
            while not keys.empty():
                k = keys.get()
                if k == "q":
                    raise KeyboardInterrupt
                if k == "m" and mode:
                    k = "c" if mode == "snapshot" else "p"
                if k in KEYS:
                    s.sendall(KEYS[k])

            try:
                data = s.recv(65536)
                if not data:
                    print("The board closed the connection.")
                    break
                buf += data
                sec["bytes"] += len(data)
                count("bytes", len(data))
            except socket.timeout:
                pass

            for kind, ts, payload in parse_packets(buf):
                if board_t0 is None:
                    board_t0 = ts
                if kind == b"HELO":
                    print("Board answered; capture starting.")
                elif kind == b"MODE":
                    new_mode, _, cause = payload.decode(errors="replace").partition(":")
                    now = time.time()
                    if mode:
                        per_mode.setdefault(mode, {"seconds": 0, "frames": 0, "audio": 0, "bytes": 0})["seconds"] += now - mode_since
                    mode, mode_since, switched = new_mode, now, True
                    changes.append((round(now - start, 3), round((ts - board_t0) / 1e6, 3), new_mode, cause))
                    print(f"[{now - start:7.1f} s] Mode -> {new_mode.upper()} ({cause})")
                elif kind == b"FRAM":
                    sec["frames"] += 1
                    count("frames")
                    if recorder:
                        size = jpeg_size(payload)
                        if size:
                            recorder.add_video(ts, payload, *size)
                elif kind == b"AUDI":
                    sec["audio"] += 1
                    count("audio")
                    if recorder:
                        recorder.add_audio(ts, payload)

            if time.time() - last >= 1:
                last = time.time()
                print(f"{(mode or 'waiting'):>10}  {sec['frames']:3d} frames/s  {sec['audio']:3d} audio/s  "
                      f"{sec['bytes'] / 1024:6.1f} KB/s" + ("  (mode changed this second)" if switched else ""))
                sec = {"bytes": 0, "frames": 0, "audio": 0}
                switched = False
    except KeyboardInterrupt:
        pass
    finally:
        try:
            s.sendall(b"X")
        except OSError:
            pass
        s.close()
        if mode:
            per_mode.setdefault(mode, {"seconds": 0, "frames": 0, "audio": 0, "bytes": 0})["seconds"] += time.time() - mode_since

    print("\nPer mode:")
    for m, st in per_mode.items():
        secs = max(st["seconds"], 1e-9)
        print(f"  {m:>10}: {st['seconds']:6.1f} s, {st['frames'] / secs:5.2f} frames/s, "
              f"{st['audio'] / secs:5.1f} audio/s, {st['bytes'] / 1024 / secs:6.1f} KB/s")
    if recorder:
        if recorder.close():
            print(f"Saved {recorder.frames} frames + audio to {name}.mkv")
        with open(f"{name}_modes.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["seconds_since_start", "board_seconds", "mode", "cause"])
            w.writerows(changes)
        print(f"Mode changes written to {name}_modes.csv")


if __name__ == "__main__":
    main()
