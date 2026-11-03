"""Logs the board's USB serial to a file: py serial_log.py PORT FILE SECONDS"""
import serial, sys, time
port, path, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
for _ in range(30):
    try: s = serial.Serial(port, 115200, timeout=0.2); break
    except Exception: time.sleep(0.3)
end = time.time() + secs
with open(path, "w") as f:
    while time.time() < end:
        line = s.readline()
        if line: f.write(line.decode(errors="replace")); f.flush()
