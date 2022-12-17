import uasyncio as aio
from machine import Pin
import network
import rp2
import urequests
import gc
from private_data import WIFI_SSID, WIFI_KEY


# board setup
rp2.country('FR')
# init I/O
led = Pin('LED', Pin.OUT)
# init network
wlan = network.WLAN(network.STA_IF)


# asyncio tasks
async def radio_task():
    while True:
        # ensure wifi is not connected
        wlan.disconnect()
        # init wlan
        wlan.active(True)
        # disable powersaving mode
        wlan.config(pm=0xa11140)

        # wlan connect
        wlan.connect(WIFI_SSID, WIFI_KEY)

        # wait for connection
        while True:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            print('waiting for connection...')
            await aio.sleep_ms(1000)

        # check network status
        if wlan.status() == network.STAT_GOT_IP:
            print(f'wifi connected, @IP={wlan.ifconfig()[0]}')

        # send LED command, escape this loop for wifi reconnect on nedd
        while True:
            if wlan.isconnected():
                led.toggle()
                try:
                    status_str = 'on' if led.value() else 'off'
                    urequests.get(f'http://192.168.4.1/{status_str}', timeout=5.0)
                    gc.collect()
                except Exception as e:
                    print(f'error occur: {e}')
                    break
            else:
                print('wifi connect lost, reconnect')
                break
            await aio.sleep_ms(1000)


async def alive_task():
    i = 0
    while True:
        print(f'{i=}')
        i += 1
        await aio.sleep_ms(1000)


# init asyncio and run
loop = aio.get_event_loop()
loop.create_task(radio_task())
loop.create_task(alive_task())
loop.run_forever()
