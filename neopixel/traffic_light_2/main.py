""" Basic traffic light test with Neopixel lib (use Pico state machine). """

import rp2
import uasyncio as aio
from lib.neopixel import Neopixel


# some const
PIX_MACHINE_ID = 0
PIX_PIN = 17
PIX_NB = 6
RED = 1
ORANGE = 2
GREEN = 3
DEBUG_STATE = {RED: 'rouge',
               ORANGE: 'orange',
               GREEN: 'vert'}
RGB_OFF = (0, 0, 0)
RGB_RED = (10, 0, 0)
RGB_ORANGE = (10, 5, 0)
RGB_GREEN = (0, 10, 0)
TL_STEPS = [(3.0, RED, GREEN),
            (3.0, RED, ORANGE),
            (3.0, RED, RED),
            (3.0, GREEN, RED),
            (3.0, ORANGE, RED),
            (3.0, RED, RED)]


# define tasks
async def tl_task():
    # init pixels
    pix = Neopixel(num_leds=PIX_NB, state_machine=PIX_MACHINE_ID, pin=PIX_PIN, mode='GRB')
    pix.brightness(255 // 10)
    # task loop
    while True:
        for (seq_delay, st_tl1, st_tl2) in TL_STEPS:
            # debug
            print(f'TL1 {DEBUG_STATE.get(st_tl1):6} TL2 {DEBUG_STATE.get(st_tl2):6}')
            # update LEDs status
            pix.set_pixel(0, RGB_RED if st_tl1 == RED else RGB_OFF)
            pix.set_pixel(1, RGB_ORANGE if st_tl1 == ORANGE else RGB_OFF)
            pix.set_pixel(2, RGB_GREEN if st_tl1 == GREEN else RGB_OFF)
            pix.set_pixel(3, RGB_RED if st_tl2 == RED else RGB_OFF)
            pix.set_pixel(4, RGB_ORANGE if st_tl2 == ORANGE else RGB_OFF)
            pix.set_pixel(5, RGB_GREEN if st_tl2 == GREEN else RGB_OFF)
            pix.show()
            # wait next step
            await aio.sleep(seq_delay)


if __name__ == '__main__':
    # ensure program is remove from state machine on rerun (avoid OSError: ENOMEM)
    rp2.PIO(PIX_MACHINE_ID).remove_program()
    # create asyncio task and run it
    loop = aio.get_event_loop()
    loop.create_task(tl_task())
    loop.run_forever()
