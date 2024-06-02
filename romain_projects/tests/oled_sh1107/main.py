"""
Test of m5stack OLED display (https://shop.m5stack.com/products/oled-unit-1-3-128-64-display)

board: Robot Pico (Cytron)
version: MicroPython v1.22.1 on 2024-01-05; Raspberry Pi Pico W with RP2040
"""

from machine import I2C, Pin
# from https://github.com/peter-l5/SH1107
from lib.sh1107 import SH1107_I2C


# I/O setup
i2c_0 = I2C(0, scl=Pin(5), sda=Pin(4), freq=800_000)
oled = SH1107_I2C(width=128, height=64, i2c=i2c_0, address=0x3c, rotate=0)


# main loop
while True:
    oled.fill(0)
    oled.text('Hello', 0, 0)
    oled.text('World', 0, 8)
    for i in range(129):
        oled.fill_rect(0, 32, 48, 8, 0)
        oled.text(f'{i=}', 0, 32)
        oled.fill_rect(0, 40, i, 8, 1)
        oled.show()
