"""
Test of Pimoroni Enviro Indoor.
https://shop.pimoroni.com/products/enviro-indoor

A Raspberry Pico W with deep sleep function (awake by an RTC chip).

Board sensors:
- BME688 4-in-1 temperature, pressure, humidity and gas sensor.
- BH1745 light (luminance and colour) sensor.

Publish sensor data into a BLE advertising payload.

Test with micropython VM from:
https://github.com/pimoroni/enviro/releases/download/v0.2.0/pimoroni-enviro-v1.22.2-micropython-enviro-v0.2.0.uf2
"""

import struct
import sys

from breakout_bme68x import BreakoutBME68X
from lib import logging
from machine import PWM, Pin
from pcf85063a import PCF85063A
from pimoroni_i2c import PimoroniI2C
from utime import sleep_ms, ticks_diff, ticks_ms

import bluetooth

# some const
# config
DEBUG_MODE = False
REFRESH_EVERY_S = 15 * 60
# IO pins
HOLD_VSYS_EN_PIN = const(2)
I2C_ID = const(0)
I2C_SDA_PIN = const(4)
I2C_SCL_PIN = const(5)
I2C_FREQ = const(100_000)
ACTIVITY_LED_PIN = const(6)
# ble
ADV_TYPE_FLAGS = const(0x01)
ADV_TYPE_NAME = const(0x09)
ADV_TYPE_UUID16_COMPLETE = const(0x3)
ADV_TYPE_UUID32_COMPLETE = const(0x5)
ADV_TYPE_UUID128_COMPLETE = const(0x7)
ADV_TYPE_SERVICE_DATA = const(0x16)
ADV_TYPE_APPEARANCE = const(0x19)
ADV_MAX_PAYLOAD = const(31)


# some function
def adv_payload(limited_disc: bool = False, br_edr: bool = False,
                name: str = '', services: list = [], service_data: list = [],
                appearance: int = 0) -> bytes:
    '''generate a payload to be passed to gap_advertise(adv_data=...)'''

    # advertising payloads are repeated packets of the following form:
    #   [1 byte data length (N bytes + 1)] [1 byte type] [N bytes type-specific data]

    payload = bytearray()

    def _append(adv_type: int, value):
        nonlocal payload
        payload += struct.pack('BB', len(value) + 1, adv_type) + value

    # add flags
    _append(ADV_TYPE_FLAGS, struct.pack('B', (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)))

    # add name
    if name:
        _append(ADV_TYPE_NAME, name)

    # add services
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(ADV_TYPE_UUID128_COMPLETE, b)

    # add service data
    if service_data:
        for uuid, raw in service_data:
            _append(ADV_TYPE_SERVICE_DATA, struct.pack('<h', uuid) + raw)

    # see org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(ADV_TYPE_APPEARANCE, struct.pack('<h', appearance))

    # check payload size
    if len(payload) > ADV_MAX_PAYLOAD:
        raise ValueError('advertising payload too large')

    return payload


# IO setup
# power rail alive pin
hold_vsys_en_pin = Pin(HOLD_VSYS_EN_PIN, Pin.OUT)
# read the state of vbus pico pin (not GPIO 2) to know if we were woken up by USB
vbus_pin = Pin('WL_GPIO2', Pin.IN)
usb_powered = bool(vbus_pin.value())
# set up the activity led
activity_led_pwm = PWM(Pin(ACTIVITY_LED_PIN))
activity_led_pwm.freq(1000)

# keep the power rail alive by holding VSYS_EN high as early as possible
hold_vsys_en_pin.value(True)
# turn on activity flag
activity_led_pwm.duty_u16(0xffff//2)

# workaround for https://github.com/micropython/micropython/issues/8904
# allow time for USB bus to enumerate
# if usb_powered:
#     sleep_ms(5000)

# logging
log_lvl = logging.WARNING
if usb_powered:
    log_lvl = logging.INFO
if DEBUG_MODE:
    log_lvl = logging.DEBUG
logging.basicConfig(level=log_lvl, stream=sys.stdout)
log = logging.Logger(__name__)
log.info(f'device is awake (usb powered={usb_powered})')

# ticks ref
tks_origin = ticks_ms()

# init I2C devices
log.info('init I2C bus')
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, I2C_FREQ)
# intialise the pcf85063a real time clock chip
log.info('init RTC')
rtc = PCF85063A(i2c)
# ensure rtc is running
i2c.writeto_mem(0x51, 0x00, b'\x00')
rtc.enable_timer_interrupt(False)

# go sleeping directly if something is wrong here
try:
    # init BLE
    ble = bluetooth.BLE()
    ble.active(True)
    # init sensors
    log.info('init sensors')
    bme688 = BreakoutBME68X(i2c, address=0x77)
    # need to write default values back into bh1745 chip otherwise it
    # reports bad results (this is undocumented...)
    i2c.writeto_mem(0x38, 0x44, b'\x02')

    # read sensors and populate dict data_d
    log.info('read sensors')
    data = bme688.read()
    temperature = round(data[0], 2)
    # pressure = round(data[1] / 100.0, 2)
    humidity = round(data[2], 2)
    # gas_resistance = round(data[3])

    # advertise
    log.info('start BLE advertise')
    adv_data = adv_payload(name='env-indoor',
                           service_data=[(0x2A6E, struct.pack('<h', int(temperature * 100))),])
    ble.gap_advertise(interval_us=125_000, connectable=False, adv_data=adv_data)
    sleep_ms(300)
except Exception as e:
    log.exc(e, 'an except occur')

# make sure the rtc flags are cleared before going back to sleep
rtc.clear_timer_flag()
rtc.clear_alarm_flag()

# set alarm to wake us up for next refresh
dt = rtc.datetime()
hour, minute, second = dt[3:6]
log.info(f'RTC current time is {hour:02}:{minute:02}:{second:02}')
wake_ds = hour * 3600 + minute * 60 + second
wake_ds += REFRESH_EVERY_S
wake_h = wake_ds // 3600
wake_m = wake_ds % 3600 // 60
wake_s = wake_ds % 60
if wake_h >= 24:
    wake_h -= 24

# sleep until next scheduled reading
log.info(f'RTC alarm (wake up time) set to {wake_h:02}:{wake_m:02}:{wake_s:02} ({REFRESH_EVERY_S} s ahead)')
rtc.set_alarm(wake_s, wake_m, wake_h)
rtc.enable_alarm_interrupt(True)

# run time calculation
run_ms = ticks_diff(ticks_ms(), tks_origin)
log.info(f'cycle run time = {run_ms/1000:.2f} s')

# disable the vsys hold, causing us to turn off
log.info('shutting down now')
hold_vsys_en_pin.value(False)

# turn off activity flag
activity_led_pwm.duty_u16(0)
