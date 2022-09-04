"""
Publish a topic to an MQTT server.
Use SSL layer and MQTT authentication.

Test on Pico W with micropythonv1.19.1.
"""

import json
import rp2
import machine
import network
import time
import ubinascii
from umqtt.simple import MQTTClient
from private_data import WIFI_SSID, WIFI_KEY, MQTT_USER, MQTT_PWD


# some functions
def blink_onboard_led(num_blinks):
    for i in range(num_blinks):
        led.on()
        time.sleep(.2)
        led.off()
        time.sleep(.2)


# init I/O
led = machine.Pin('LED', machine.Pin.OUT)

# init wlan
rp2.country('FR')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# disable powersaving mode
wlan.config(pm = 0xa11140)

# See the MAC address in the wireless chip OTP
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print(f'@MAC is {mac}')

# wlan connect
wlan.connect(WIFI_SSID, WIFI_KEY)

# wait for connection with 10 second timeout
timeout = 10
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('waiting for connection...')
    time.sleep(1)

# check network status
wlan_status = wlan.status()
blink_onboard_led(wlan_status)
if wlan_status == network.STAT_GOT_IP:
    print('wifi connected')
    print(f'@IP is {wlan.ifconfig()[0]}')
else:
    raise RuntimeError('wifi connection failed')

# build SSL MQTT client (warn: here we don't validate server certificate)
client_id = ubinascii.hexlify(machine.unique_id())
ssl_d = {'key': open('/crt/mqtt-cli-pico-w.der.key').read(),
         'cert': open('/crt/mqtt-cli-pico-w.der.crt').read()}
mcl = MQTTClient(client_id=client_id, server='192.168.1.60', port=8883,
                 user=MQTT_USER, password=MQTT_PWD, ssl=True, ssl_params=ssl_d)
print('connect to MQTT server... ', end='')
mcl.connect()
print('OK')

# publish loop
for i in range(3):
    topic = b'test/mytopic'
    payload = json.dumps(dict(loop=i)).encode()
    print(f'MQTT publish: {topic=}, {payload=}')
    mcl.publish(topic, payload)
    time.sleep(1.0)

# MQTT disconnect
mcl.disconnect()
