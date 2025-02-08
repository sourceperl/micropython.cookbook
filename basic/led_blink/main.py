import time

import machine

led = machine.Pin('LED', machine.Pin.OUT)

while True:
    led.toggle()
    time.sleep(.2)
