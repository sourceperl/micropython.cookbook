#!/usr/bin/env python3

import argparse
from serial import Serial, serialutil


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('device', type=str, help='serial device (like /dev/ttyUSB0)')
parser.add_argument('-b', '--baudrate', type=int, default=9600, help='serial rate (default is 9600)')
parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
args = parser.parse_args()

# serial try
try:
    # init serial
    ser = Serial(port=args.device, baudrate=args.baudrate)
    # work
    while True:
        line = ser.readline().decode().strip()
        if 'ERR' in line:
            print(line)
except serialutil.SerialException as e:
    print(f'serial error: {e}')
    exit(1)
