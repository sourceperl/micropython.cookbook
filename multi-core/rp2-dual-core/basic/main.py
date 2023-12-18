"""
Basic test of dual-cores code on an RP2040 (Pico).

- core0 task: toggle thread lock every 1s and print it's status.
- core1 task: blink onboard LED while thread lock is not acquire by core0.
"""

import _thread
from machine import Pin
from utime import sleep_ms


def core0_task():
    # task init
    pass
    # main loop
    while True:
        sleep_ms(1_000)
        thread_lock.acquire()
        print('lock acquire (stop blink)')
        sleep_ms(1_000)
        thread_lock.release()
        print('lock release (allow blink)')


def core1_task():
    # task init
    led = Pin(25, Pin.OUT)
    # main loop
    while True:
        # LED blink (if no thread lock)
        with thread_lock:
            led.on()
            sleep_ms(40)
            led.off()
            sleep_ms(100)


# global init
thread_lock = _thread.allocate_lock()

# launch 2nd and 1st core task
_thread.start_new_thread(core1_task, ())
core0_task()
