"""Test of m5stack color unit (use TCS34725 chip)

more info: https://docs.m5stack.com/en/unit/color
"""

from machine import I2C, Pin
import neopixel
from utime import sleep_ms
from lib.tcs34725 import TCS34725, html_rgb, html_hex


# init I2C bus and TCS34725
i2c = I2C(id=0, scl=Pin(5), sda=Pin(4))
sensor = TCS34725(i2c)
sensor.gain(16)
# init neopixel
np = neopixel.NeoPixel(Pin(18), 2)

# main loop
while True:
    # read TCS34725 data
    data = sensor.read(raw=True)
    r, g, b = html_rgb(data)
    hex_str = html_hex(data)
    # show results
    print(f'{r=:5.01f} {g=:5.01f} {b=:5.01f} as hex str: #{hex_str}')
    # apply current color to neopixel
    np.fill(list(map(round, (r, g, b))))
    np.write()
    # next loop in 200 ms
    sleep_ms(200)
