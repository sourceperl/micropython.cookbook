import rp2
from utime import sleep_ms
from machine import Pin
from lib.neopixel import Neopixel


# some const
PIX_MACHINE_ID = 0
PIX_PIN = 15
PIX_NB = 50


# ensure program is remove from state machine on rerun (avoid OSError: ENOMEM)
rp2.PIO(PIX_MACHINE_ID).remove_program()
# init pixels
pix = Neopixel(num_leds=PIX_NB, state_machine=PIX_MACHINE_ID, pin=PIX_PIN, mode='GRB')
pix.brightness(255//10)

# main loop
hue = 0
while True:
    pix.fill(pix.colorHSV(hue, 255, 150))
    pix.show()
    hue += 25
    hue %= 0xffff
