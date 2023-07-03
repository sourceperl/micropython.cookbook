""" Send a json message with POST method to an HTTP server. """

import rp2
import network
import time
import urequests
from private_data import WIFI_SSID, WIFI_KEY


# init wlan
rp2.country('FR')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
# disable powersaving mode
wlan.config(pm=0xa11140)

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
if wlan.status() == network.STAT_GOT_IP:
    print(f'wifi connected (@IP {wlan.ifconfig()[0]})')
else:
    raise RuntimeError('wifi connection failed')

# publish json message with HTTP POST
r = urequests.post('http://192.168.1.45:8080/api/test', json=dict(foo='hello'))

if r.status_code == 200:
    print(f'HTTP POST status: success')
else:
    print(f'HTTP POST status: error')
