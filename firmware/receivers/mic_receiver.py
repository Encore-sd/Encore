"""
Live listener for mic_stream.ino (XIAO ESP32S3 Sense).

Plays the board's microphone through your speakers and saves it to mic_test.wav.
Usage:  python mic_receiver.py COM5
        python mic_receiver.py          (lists available ports)
Press Ctrl+C to stop.
"""
import sys
import wave

import serial
import serial.tools.list_ports
import sounddevice as sd

SAMPLE_RATE = 16000
OUT_FILE = "mic_test.wav"


def main():
    if len(sys.argv) < 2:
        print("Usage: python mic_receiver.py <PORT>\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}  {p.description}")
        return

    ser = serial.Serial(sys.argv[1], 115200, timeout=1)
    ser.reset_input_buffer()
    ser.write(b"S")

    leftover = b""
    try:
        with wave.open(OUT_FILE, "wb") as wav, sd.RawOutputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16"
        ) as out:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            print(f"Streaming from {sys.argv[1]} - saving to {OUT_FILE}. Ctrl+C to stop.")
            while True:
                data = leftover + ser.read(ser.in_waiting or 1024)
                usable = len(data) - len(data) % 2  # keep whole 16-bit samples
                leftover = data[usable:]
                if usable:
                    out.write(data[:usable])
                    wav.writeframes(data[:usable])
    except KeyboardInterrupt:
        pass
    finally:
        ser.write(b"X")
        ser.close()
        print(f"\nStopped. Recording saved to {OUT_FILE}")


if __name__ == "__main__":
    main()
