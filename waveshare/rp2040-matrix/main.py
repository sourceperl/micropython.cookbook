"""
Test of RP2040-Matrix with an example of a basic traffic light.

https://www.waveshare.com/wiki/RP2040-Matrix
"""

from machine import Pin
from neopixel import NeoPixel
import time


# some const
class Color:
    # color scheme: (GREEN, RED, BLUE)
    BLANK = (0, 0, 0)
    RED = (0, 6, 0)
    ORANGE = (3, 6, 0)
    GREEN = (6, 0, 0)


# global vars
steps_l = [{'tl1': Color.RED, 'tl2': Color.GREEN, 'wait_s': 2.0},
           {'tl1': Color.RED, 'tl2': Color.ORANGE, 'wait_s': 1.5},
           {'tl1': Color.RED, 'tl2': Color.RED, 'wait_s': 0.8},
           {'tl1': Color.GREEN, 'tl2': Color.RED, 'wait_s': 2.0},
           {'tl1': Color.ORANGE, 'tl2': Color.RED, 'wait_s': 1.5},
           {'tl1': Color.RED, 'tl2': Color.RED, 'wait_s': 0.8}]


# I/O setup
# 5x5 LEDs matrix
np_mtx = NeoPixel(Pin(16), 25)
# clear
np_mtx.fill(Color.BLANK)
np_mtx.write()
# steps loop
while True:
    for step_idx, step_d in enumerate(steps_l):
        # print current step
        step = step_idx + 1
        print(f'step {step}', end='\r')
        # traffic light 1
        for i in range(5):
            np_mtx[i] = step_d['tl1']
        # traffic light 2
        for i in range(5):
            np_mtx[i+20] = step_d['tl2']
        # apply
        np_mtx.write()
        time.sleep(step_d['wait_s'])
