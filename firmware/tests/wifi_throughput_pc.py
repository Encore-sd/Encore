"""
Receiver for wifi_throughput_test.ino: connects to the board's TCP port 5001
and reports received KB/s each second.
Usage: py wifi_throughput_pc.py HOST [seconds]
"""
import socket
import sys
import time

HOST = sys.argv[1]
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20

s = socket.create_connection((HOST, 5001), timeout=5)
s.settimeout(0.2)
per_second = []
got = 0
start = last = time.time()
while time.time() - start < SECONDS:
    try:
        data = s.recv(262144)
        if not data:
            break
        got += len(data)
    except socket.timeout:
        pass
    if time.time() - last >= 1:
        kbs = got / 1024 / (time.time() - last)
        per_second.append(kbs)
        print(f"received {kbs:7.1f} KB/s")
        got = 0
        last = time.time()
s.close()

steady = per_second[2:] or per_second  # skip the first seconds while TCP ramps up
print(f"\nAverage {sum(steady) / len(steady):.1f} KB/s ({sum(steady) / len(steady) * 8 / 1024:.2f} Mbit/s), "
      f"min {min(steady):.1f}, max {max(steady):.1f}")
