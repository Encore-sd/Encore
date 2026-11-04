"""
Audio-only version of stream_rate.py, for power measurements of audio capture.
Pair with av_wifi_audio.ino (the camera is never started). Connects, starts a
recording ('R'), counts audio packets and bytes each second and checks for gaps
in the audio, then stops.
Usage: py stream_rate_audio_only.py HOST [seconds]
"""
import socket
import struct
import sys
import time

HOST = sys.argv[1]
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
HEADER = struct.Struct("<4sQI")
TYPES = {b"AUDI", b"FRAM", b"STRT", b"STOP", b"HELO"}
SAMPLE_RATE = 16000
EXPECTED_PER_S = SAMPLE_RATE / 512  # 31.25 packets of 512 samples

s = socket.create_connection((HOST, 5000), timeout=5)
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
s.settimeout(0.2)
s.sendall(b"S")
time.sleep(0.5)
s.sendall(b"R")

buf = bytearray()
rows = []
sec = {"bytes": 0, "audio": 0, "audio_bytes": 0}
frames = 0        # video frames: there should be none with av_wifi_audio.ino
gaps = 0          # audio chunks the board dropped (seen as jumps in the timestamps)
next_ts = None
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
        kind, ts, length = HEADER.unpack_from(buf, pos)
        if kind not in TYPES or length > 1_000_000:
            pos += 1
            continue
        if len(buf) - pos < HEADER.size + length:
            break
        if kind == b"AUDI":
            sec["audio"] += 1
            sec["audio_bytes"] += length
            if next_ts is not None and ts > next_ts + 1000:  # more than 1 ms late = chunk missing
                gaps += 1
            next_ts = ts + (length // 2) * 1_000_000 // SAMPLE_RATE
        elif kind == b"FRAM":
            frames += 1
        pos += HEADER.size + length
    del buf[:pos]
    if time.time() - last >= 1:
        last = time.time()
        rows.append(dict(sec))
        print(f"{sec['bytes'] / 1024:6.1f} KB/s  {sec['audio']:3d} audio/s")
        sec = {"bytes": 0, "audio": 0, "audio_bytes": 0}

s.sendall(b"E")
time.sleep(0.3)
s.sendall(b"X")
s.close()

steady = rows[2:] or rows  # skip the start-up seconds
kbs = [r["bytes"] / 1024 for r in steady]
audio = [r["audio"] for r in steady]
print(f"\nAverage {sum(kbs) / len(kbs):.1f} KB/s (min {min(kbs):.1f}, max {max(kbs):.1f}), "
      f"{sum(audio) / len(audio):.1f} audio packets/s ({EXPECTED_PER_S} expected), "
      f"{gaps} gaps in the audio")
if frames:
    print(f"WARNING: {frames} video frames arrived - the board is running av_wifi.ino, not av_wifi_audio.ino")
