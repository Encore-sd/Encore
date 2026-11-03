"""
Measures the real stream from av_ble.ino over Bluetooth without a window or audio:
connects, starts a recording ('R'), counts packets and bytes each second, then stops.
Usage: py ble_stream_rate.py [seconds]
"""
import asyncio
import struct
import sys
import time

from bleak import BleakClient, BleakScanner

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
HEADER = struct.Struct("<4sQI")
TYPES = {b"AUDI", b"FRAM", b"STRT", b"STOP", b"HELO"}


async def main():
    device = await BleakScanner.find_device_by_name("XIAO-AV", timeout=20)
    if device is None:
        print("Not found - is av_ble.ino running?")
        return
    buf = bytearray()
    sec = {"bytes": 0, "frames": 0, "audio": 0, "frame_bytes": 0}
    seen = set()

    def on_data(_, data):
        buf.extend(data)
        sec["bytes"] += len(data)
        pos = 0
        while len(buf) - pos >= HEADER.size:
            kind, _, length = HEADER.unpack_from(buf, pos)
            if kind not in TYPES or length > 1_000_000:
                pos += 1
                continue
            if len(buf) - pos < HEADER.size + length:
                break
            seen.add(kind)
            if kind == b"FRAM":
                sec["frames"] += 1
                sec["frame_bytes"] += length
            elif kind == b"AUDI":
                sec["audio"] += 1
            pos += HEADER.size + length
        del buf[:pos]

    async with BleakClient(device) as client:
        print(f"Connected, MTU {client.mtu_size}")
        await client.start_notify(TX_UUID, on_data)
        await client.write_gatt_char(RX_UUID, b"S", response=True)
        await asyncio.sleep(1)
        await client.write_gatt_char(RX_UUID, b"R", response=True)
        rows = []
        for _ in range(SECONDS):
            for k in sec:
                sec[k] = 0
            await asyncio.sleep(1)
            rows.append(dict(sec))
            r = rows[-1]
            avg = r["frame_bytes"] / r["frames"] / 1024 if r["frames"] else 0
            print(f"{r['bytes'] / 1024:6.1f} KB/s  {r['frames']:3d} fps  {r['audio']:3d} audio/s  frame {avg:4.1f} KB")
        await client.write_gatt_char(RX_UUID, b"E", response=True)
        await asyncio.sleep(1)
        await client.write_gatt_char(RX_UUID, b"X", response=True)

    steady = rows[2:] or rows
    kbs = [r["bytes"] / 1024 for r in steady]
    fps = [r["frames"] for r in steady]
    frames = sum(fps)
    print(f"\nPackets seen: {sorted(k.decode() for k in seen)}")
    print(f"Average {sum(kbs) / len(kbs):.1f} KB/s (min {min(kbs):.1f}, max {max(kbs):.1f}), "
          f"{sum(fps) / len(fps):.1f} fps (min {min(fps)}, max {max(fps)}), "
          f"{sum(r['audio'] for r in steady) / len(steady):.1f} audio packets/s, "
          f"frame {sum(r['frame_bytes'] for r in steady) / max(frames, 1) / 1024:.1f} KB")


asyncio.run(main())
