# traffic light (3 states) system

from machine import Pin
import neopixel
import uasyncio as aio


# some const
class State:
    RED = 1
    ORANGE = 2
    GREEN = 3

class LED:
    BLANK = (0,0,0)
    RED = (10,0,0)
    ORANGE = (10,5,0)
    GREEN = (0,10,0)

# some functions
def traffic_light_set(np_obj, tl_status):
    # RED area
    for i in range(0, 4):
        if State.RED in tl_status:
            np_obj[i] = LED.RED
        else:
            np_obj[i] = LED.BLANK
    # ORANGE area
    for i in range(4, 7):
        if State.ORANGE in tl_status:
            np_obj[i] = LED.ORANGE
        else:
            np_obj[i] = LED.BLANK
    # GREEN area
    for i in range(7, 10):
        if State.GREEN in tl_status:
            np_obj[i] = LED.GREEN
        else:
            np_obj[i] = LED.BLANK
    # I/O to LEDs
    np_obj.write()


# global vars
cur_step = 1
steps_conf = {1: {1: (State.RED,), 2: (State.GREEN,)},
              2: {1: (State.RED,), 2: (State.ORANGE,)},
              3: {1: (State.RED,), 2: (State.RED,)},
              4: {1: (State.GREEN,), 2: (State.RED,)},
              5: {1: (State.ORANGE,), 2: (State.RED,)},
              6: {1: (State.RED,), 2: (State.RED,)},
             }

# LED stick init (2 sticks of 10 leds ws2813)
np_tl1 = neopixel.NeoPixel(Pin(16), 10)
np_tl2 = neopixel.NeoPixel(Pin(18), 10)

# define tasks
async def step_seq_task():
    global cur_step
    # define steps sequence as (step_id, duration) tuples list
    seq = [(1, 3.0), (2, 3.0), (3, 3.0), (4, 3.0), (5, 3.0), (6, 3.0)]
    # task loop
    while True:
        for (step_id, duration) in seq:
            cur_step = step_id
            await aio.sleep(duration)


async def tl_leds_task():
    global cur_step
    # task loop
    while True:
        # get current step conf
        step_cnf_d = steps_conf.get(cur_step, {})
        # traffic light 1
        traffic_light_set(np_tl1, step_cnf_d.get(1, ()))
        # traffic light 2
        traffic_light_set(np_tl2, step_cnf_d.get(2, ()))
        # wait 0.5s
        await aio.sleep(0.5)


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(step_seq_task())
loop.create_task(tl_leds_task())
loop.run_forever()
