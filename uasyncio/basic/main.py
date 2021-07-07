import uasyncio
import gc
from machine import Pin

# task 1
async def led_blink():
    led = Pin(25, Pin.OUT)
    while True:
        led.on()
        await uasyncio.sleep_ms(100)
        led.off()
        await uasyncio.sleep_ms(100)

# task 2
async def say_hello():
    while True:
        print('time to say hello !')
        await uasyncio.sleep_ms(1_000)

# task 3
async def mem_report():
    while True:
        print('free mem = %s' % gc.mem_free())
        await uasyncio.sleep_ms(5_000)

# main task
async def main():
    # create task
    uasyncio.create_task(led_blink())
    uasyncio.create_task(say_hello())
    uasyncio.create_task(mem_report())
    # main loop
    while True:
        print('main() is alive')
        await uasyncio.sleep_ms(2_000)

# run
uasyncio.run(main())
