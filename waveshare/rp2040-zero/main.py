import time

from machine import Pin

from neopixel import NeoPixel

# some const
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
INDIGO = (75, 0, 130)
VIOLET = (138, 43, 226)
COLORS = (RED, ORANGE, YELLOW, GREEN, BLUE, INDIGO, VIOLET)


# init RGB led
np = NeoPixel(pin=Pin(16), n=1)

while True:
    for color in COLORS:
        np.fill(color)
        np.write()
        time.sleep_ms(6_00)
