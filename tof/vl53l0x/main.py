import time
from machine import Pin, I2C
# from https://github.com/kevinmcaleer/vl53l0x
from vl53l0x import VL53L0X


# init I/O
i2c_0 = I2C(0, sda=Pin(8), scl=Pin(9))
tof = VL53L0X(i2c_0)

# infinite loop
while True:
    d = tof.ping()
    print(f'{d} mm', end='\r')
    time.sleep(1)
