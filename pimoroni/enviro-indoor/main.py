"""
Test of Pimoroni Enviro Indoor.
https://shop.pimoroni.com/products/enviro-indoor

A Raspberry Pico W with deep sleep function (awake by an RTC chip).

Board sensors:
- BME688 4-in-1 temperature, pressure, humidity and gas sensor.
- BH1745 light (luminance and colour) sensor.

Push sensors data as a json message to an MQTT server (with SSL).

Test with micropython VM from:
https://github.com/pimoroni/enviro/releases/download/v0.0.9/pimoroni-picow_enviro-v1.19.10-micropython-v0.0.9.uf2
"""


import rp2
from machine import Pin, PWM, unique_id
import math
import network
import json
from utime import sleep_ms
import ubinascii
from ucollections import OrderedDict
from umqtt.simple import MQTTClient
from pimoroni_i2c import PimoroniI2C
from pcf85063a import PCF85063A
from breakout_bme68x import BreakoutBME68X
from breakout_bh1745 import BreakoutBH1745
from lib.misc import lux_from_rgbc, colour_temperature_from_rgbc
from private_data import WIFI_SSID, WIFI_KEY, MQTT_USER, MQTT_PWD


# some const
# config
REFRESH_EVERY_S = 15 * 60
# IO pins
HOLD_VSYS_EN_PIN = 2
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
ACTIVITY_LED_PIN = 6

# IO setup
# power rail alive pin
hold_vsys_en_pin = Pin(HOLD_VSYS_EN_PIN, Pin.OUT)
# read the state of vbus to know if we were woken up by USB
vbus_present_pin = Pin('WL_GPIO2', Pin.IN)
# set up the activity led
activity_led_pwm = PWM(Pin(ACTIVITY_LED_PIN))
activity_led_pwm.freq(1000)
activity_led_pwm.duty_u16(0)

# keep the power rail alive by holding VSYS_EN high as early as possible
hold_vsys_en_pin.value(True)
# turn on activity flag
activity_led_pwm.duty_u16(0xffff//2)

# init wlan
rp2.country('FR')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# wlan connect
wlan.connect(WIFI_SSID, WIFI_KEY)
# disable powersaving mode
wlan.config(pm = 0xa11140)
# init I2C devices
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, 100000)
bme688 = BreakoutBME68X(i2c, address=0x77)
bh1745 = BreakoutBH1745(i2c, address=0x38)
# need to write default values back into bh1745 chip otherwise it
# reports bad results (this is undocumented...)
i2c.writeto_mem(0x38, 0x44, b'\x02')
# intialise the pcf85063a real time clock chip
rtc = PCF85063A(i2c)
i2c.writeto_mem(0x51, 0x00, b'\x00') # ensure rtc is running (this should be default?)
rtc.enable_timer_interrupt(False)

# read sensors and populate dict data_d
data = bme688.read()
temperature = round(data[0], 2)
pressure = round(data[1] / 100.0, 2)
humidity = round(data[2], 2)
gas_resistance = round(data[3])
# an approximate air quality calculation that accounts for the effect of
# humidity on the gas sensor
# https://forums.pimoroni.com/t/bme680-observed-gas-ohms-readings/6608/25
aqi = round(math.log(gas_resistance) + 0.04 * humidity, 1)
bh1745.measurement_time_ms(160)
r, g, b, c = bh1745.rgbc_raw()
data_d = OrderedDict({'temperature': temperature, 'humidity': humidity, 'pressure': pressure,
                      'gas_resistance': gas_resistance, 'aqi': aqi, 'luminance': lux_from_rgbc(r, g, b, c),
                      'color_temperature': colour_temperature_from_rgbc(r, g, b, c)})

# WLAN: wait for connection with 10 second timeout
timeout = 10
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('waiting for connection...')
    sleep_ms(1000)

# check network status
wlan_status = wlan.status()
if wlan_status == network.STAT_GOT_IP:
    print('wifi connected')
    print(f'@IP is {wlan.ifconfig()[0]}')
else:
    raise RuntimeError('wifi connection failed')

# build SSL MQTT client (warn: here we don't validate server certificate)
client_id = ubinascii.hexlify(unique_id())
ssl_d = {'key': open('/crt/mqtt-cli-pico-w.der.key').read(),
         'cert': open('/crt/mqtt-cli-pico-w.der.crt').read()}
mcl = MQTTClient(client_id=client_id, server='192.168.1.60', port=8883,
                 user=MQTT_USER, password=MQTT_PWD, ssl=True, ssl_params=ssl_d)
print('connect to MQTT server... ', end='')
mcl.connect()
print('OK')

# publish loop
topic = b'test/mytopic'
payload = json.dumps(data_d).encode()
print(f'MQTT publish: {topic=}, {payload=}')
mcl.publish(topic, payload)

# MQTT disconnect
mcl.disconnect()

# show result
print(f'VBUS present {vbus_present_pin.value()=}')
print('')
for k,v in data_d.items():
    print(f'{k} = {v}')

# make sure the rtc flags are cleared before going back to sleep
print('')
print('clearing and disabling previous alarm')
rtc.clear_timer_flag()
rtc.clear_alarm_flag()

# set alarm to wake us up for next refresh
dt = rtc.datetime()
hour, minute, second = dt[3:6]
wake_ds = hour * 3600 + minute * 60 + second
wake_ds += REFRESH_EVERY_S
wake_h = wake_ds // 3600
wake_m = wake_ds % 3600 // 60
wake_s = wake_ds % 60
if wake_h >= 24:
    wake_h -= 24

print(f'{dt=}')
print(f'setting alarm to wake at {wake_h:02}:{wake_m:02}:{wake_s:02}')

# sleep until next scheduled reading
rtc.set_alarm(wake_s, wake_m, wake_h)
rtc.enable_alarm_interrupt(True)

# disable the vsys hold, causing us to turn off
print('shutting down')
hold_vsys_en_pin.value(False)

# turn off activity flag
activity_led_pwm.duty_u16(0)
