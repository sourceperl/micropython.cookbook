#!/usr/bin/env python3

"""Send a random modbus RTU frame for testing purposes."""

import argparse
import os
import time
from random import randint

from serial import Serial, serialutil


# some functions
def crc16(frame: bytes) -> int:
    """Return CRC16 of current frame."""
    crc = 0xFFFF
    for next_byte in frame:
        crc ^= next_byte
        for _ in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc


if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('device', type=str, help='serial device (like /dev/ttyUSB0)')
    parser.add_argument('-b', '--baudrate', type=int, default=9600, help='serial rate (default is 9600)')
    parser.add_argument('-w', '--wait', type=float, default=0.5, help='wait between frame (default is 0.5 s)')
    parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
    args = parser.parse_args()

    # serial try
    try:
        # init serial
        serial = Serial(port=args.device, baudrate=args.baudrate)
        # main loop
        while True:
            # build a random modbus frame (size from 10 to 256 bytes) with CRC
            frame = os.urandom(randint(8, 254))
            frame += crc16(frame).to_bytes(2, byteorder='little')
            # debug
            if args.debug:
                frame_as_str = '-'.join(f'{x:02X}' for x in frame)
                print(f'send {len(frame)} bytes: {frame_as_str}')
            # send it
            serial.write(frame)
            # wait before next send
            time.sleep(args.wait)
    except serialutil.SerialException as e:
        print(f'serial error: {e}')
        exit(1)
