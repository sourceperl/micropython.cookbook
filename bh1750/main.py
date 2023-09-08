from machine import Pin, I2C
from utime import sleep_ms
from lib.bh1750 import BH1750


# init
i2c = I2C(0, sda=Pin(4), scl=Pin(5))
bh1750 = BH1750(0x23, i2c)

# main loop
while True:
    lux = round(bh1750.measurement)
    print(f'{lux} lux')
    sleep_ms(500)
