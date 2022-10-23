"""Test of m5stack voltmeter unit (use ADS1115 chip)

more info: https://docs.m5stack.com/en/unit/vmeter
"""

from utime import sleep
from machine import I2C, Pin
from ads1x15 import ADS1115


# some const
RES_RATIO = 1/(11/(11+680))

# inits
i2c = I2C(id=0, sda=Pin(8), scl=Pin(9))
adc = ADS1115(i2c=i2c, address=0x49, gain=4)

# read loop
while True:
    # read diff AINO - AIN1
    raw = adc.read(rate=1, channel1=0, channel2=1)
    # decode RAW value (gain=0 > +/-6_144mv > 1 bit = 0.1875mv)
    # volts = RES_RATIO * -raw * 0.1875 / 1000
    # decode RAW value (gain=4 > +/-0_512mv > 1 bit = 0.015625mv)
    volts = RES_RATIO * -raw * 0.015625 / 1000
    print(f'value: {volts:0.3f} V (raw: {raw})')
    sleep(2.0)
