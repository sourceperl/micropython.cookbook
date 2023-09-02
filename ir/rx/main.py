"""Test of m5stack IR remote unit

more info: https://shop.m5stack.com/products/ir-unit
IR lib: https://github.com/peterhinch/micropython_ir
"""

import gc
from machine import Pin
from utime import sleep_ms
from lib.ir_rx.nec import NEC_8


# some functions
def ir_user_cb(data, addr, ctrl):
    # NEC protocol sends repeat codes (with data < 0)
    if data < 0:
        return
    print(f'data 0x{data:02x} addr 0x{addr:04x} ctrl 0x{ctrl:02x}')
    if data == 0x08 and addr == 0x0004 and ctrl == 0x00:
        print("it's a press of the power button")


# init NEC_8 decode with IR receiver module (IRM-3638T) at GPIO 3
ir = NEC_8(pin=Pin(3, Pin.IN), callback=ir_user_cb)
# main loop
try:
    while True:
        # A real application would do something here...
        sleep_ms(5_000)
        gc.collect()
except KeyboardInterrupt:
    ir.close()
