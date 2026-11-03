"""
Receiver for ble_throughput_test.ino: connects to XIAO-BLE-TEST, subscribes to
the data characteristic and reports received KB/s and lost packets each second.
Usage: python ble_throughput_pc.py [seconds]   (needs: pip install bleak)
"""
import asyncio
import struct
import sys
import time

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "XIAO-BLE-TEST"
DATA_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20


async def main():
    print(f"Scanning for {DEVICE_NAME}...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=15)
    if device is None:
        print("Not found - is the test sketch running?")
        return

    stats = {"bytes": 0, "packets": 0, "lost": 0, "next_seq": None, "size": 0}

    def on_data(_, data: bytearray):
        seq = struct.unpack_from("<I", data)[0]
        if stats["next_seq"] is not None and seq > stats["next_seq"]:
            stats["lost"] += seq - stats["next_seq"]
        stats["next_seq"] = seq + 1
        stats["bytes"] += len(data)
        stats["packets"] += 1
        stats["size"] = len(data)

    async with BleakClient(device) as client:
        print(f"Connected, MTU {client.mtu_size}")
        await client.start_notify(DATA_UUID, on_data)
        per_second = []
        for _ in range(SECONDS):
            before = stats["bytes"]
            await asyncio.sleep(1)
            kbs = (stats["bytes"] - before) / 1024
            per_second.append(kbs)
            print(f"received {kbs:6.1f} KB/s  (payload {stats['size']} bytes, lost so far {stats['lost']})")
        try:
            await client.stop_notify(DATA_UUID)
        except OSError:
            pass  # Windows sometimes cancels this while disconnecting; the measurement is already done

    steady = per_second[2:] or per_second  # skip the first seconds while settings are negotiated
    print(f"\nAverage {sum(steady) / len(steady):.1f} KB/s, min {min(steady):.1f}, max {max(steady):.1f}, "
          f"{stats['packets']} packets, {stats['lost']} lost")


asyncio.run(main())
