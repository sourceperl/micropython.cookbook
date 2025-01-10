""" A BLE advertissing sample with a custom payload to publish temperature as service data. """

import random
import struct

from machine import Pin
from micropython import const

import bluetooth
import uasyncio as aio

# some const
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


def t_encode(temp_deg_c: float) -> bytes:
    '''encode temperature for bluetooth.
    -> as seen in GATT Specification Supplement (GSS) at https://www.bluetooth.com/specifications/gss/)
    '''
    return struct.pack('<h', int(temp_deg_c * 100))


async def adv_task():
    '''BLE advertise with a custom payload'''
    # init BLE
    ble = bluetooth.BLE()
    ble.active(True)
    # advertise loop
    while True:
        temp_deg_c = 25.00 + random.uniform(-0.5, 0.5)
        adv_data = adv_payload(name='ble-temp-adv',
                               service_data=[(0x2A6E, t_encode(temp_deg_c)),])
        ble.gap_advertise(interval_us=250_000, connectable=False, adv_data=adv_data)
        await aio.sleep_ms(2_000)


async def led_task():
    '''life indicator in the form of flashing LED'''
    # I/O init
    led = Pin('LED', Pin.OUT)
    # main loop
    while True:
        led.on()
        await aio.sleep_ms(75)
        led.off()
        await aio.sleep_ms(300)


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(adv_task())
loop.create_task(led_task())
loop.run_forever()
