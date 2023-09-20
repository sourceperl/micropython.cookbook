"""Test of m5stack TVOC/eCO2 gas sensor unit (use SGP30 chip)

more info: https://docs.m5stack.com/en/unit/tvoc
"""

from machine import Pin, I2C
import time
# from https://github.com/jeroenhuijzer/SGP30-micropython
from lib.sgp30 import SGP30


# initialize I2C bus
i2c = I2C(0, scl=Pin(5), sda=Pin(4))

# initialize SGP30 chip
sensor = SGP30(i2c)
sensor.sgp30_probe()
print('SGP sensor probing successful')
feature_set_version, product_type = sensor.sgp30_get_feature_set_version()
print(f'feature set version: {feature_set_version}')
print(f'product type: {product_type}')
serial_id = sensor.sgp30_get_serial_id()
print(f'serial ID: {serial_id}')

# read gas raw signals
ethanol_raw_signal, h2_raw_signal = sensor.sgp30_measure_raw_blocking_read()
print(f'Ethanol raw signal: {ethanol_raw_signal}')
print(f'H2 raw signal: {h2_raw_signal}')

# if no baseline is available or the most recent baseline is more than
# one week old, it must discarded. A new baseline is found with sgp30_iaq_init
sensor.sgp30_iaq_init()
print('sgp30_iaq_init done')

# run periodic IAQ measurements at defined intervals
while True:
    tvoc_ppb, co2_eq_ppm = sensor.sgp30_measure_iaq_blocking_read()
    print(f'tVOC  Concentration: {tvoc_ppb} ppb')
    print(f'CO2eq Concentration: {co2_eq_ppm} ppm')
    # the IAQ measurement must be triggered exactly once per second (SGP30)
    # to get accurate values.
    time.sleep(1)
