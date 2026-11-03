"""
Measures the real stream from av_wifi_sta.ino / av_wifi.ino over TCP: connects,
starts a recording ('R'), counts packets and bytes each second, then stops.
Usage: py stream_rate.py HOST [seconds]
"""
import socket
import struct
import sys
import time

HOST = sys.argv[1]
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
HEADER = struct.Struct("<4sQI")
TYPES = {b"AUDI", b"FRAM", b"STRT", b"STOP", b"HELO"}

s = socket.create_connection((HOST, 5000), timeout=5)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
s.settimeout(0.2)
s.sendall(b"S")
time.sleep(0.5)
s.sendall(b"R")

buf = bytearray()
rows = []
sec = {"bytes": 0, "frames": 0, "audio": 0, "frame_bytes": 0}
start = last = time.time()
while time.time() - start < SECONDS:
    try:
        data = s.recv(65536)
        if not data:
            break
        buf += data
        sec["bytes"] += len(data)
    except socket.timeout:
        pass
    pos = 0
    while len(buf) - pos >= HEADER.size:
        kind, _, length = HEADER.unpack_from(buf, pos)
        if kind not in TYPES or length > 1_000_000:
            pos += 1
            continue
        if len(buf) - pos < HEADER.size + length:
            break
        if kind == b"FRAM":
            sec["frames"] += 1
            sec["frame_bytes"] += length
        elif kind == b"AUDI":
            sec["audio"] += 1
        pos += HEADER.size + length
    del buf[:pos]
    if time.time() - last >= 1:
        last = time.time()
        rows.append(dict(sec))
        avg_frame = sec["frame_bytes"] / sec["frames"] / 1024 if sec["frames"] else 0
        print(f"{sec['bytes'] / 1024:6.0f} KB/s  {sec['frames']:3d} fps  {sec['audio']:3d} audio/s  frame {avg_frame:4.1f} KB")
        sec = {"bytes": 0, "frames": 0, "audio": 0, "frame_bytes": 0}

s.sendall(b"E")
time.sleep(0.3)
s.sendall(b"X")
s.close()

steady = rows[2:] or rows  # skip the start-up seconds
kbs = [r["bytes"] / 1024 for r in steady]
fps = [r["frames"] for r in steady]
frames = sum(r["frames"] for r in steady)
print(f"\nAverage {sum(kbs) / len(kbs):.0f} KB/s (min {min(kbs):.0f}, max {max(kbs):.0f}), "
      f"{sum(fps) / len(fps):.1f} fps (min {min(fps)}, max {max(fps)}), "
      f"{sum(r['audio'] for r in steady) / len(steady):.1f} audio packets/s, "
      f"frame {sum(r['frame_bytes'] for r in steady) / max(frames, 1) / 1024:.1f} KB")
