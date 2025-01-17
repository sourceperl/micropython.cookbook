""" 
A simple peripheral BLE device, providing a standard "device information" service and a custom UUID 0xffe0 service.


"""

import aioble
from machine import Pin

import uasyncio as aio
from bluetooth import UUID

# some const
UUID_SVC_DEV_INFO = UUID(0x180A)
UUID_CHAR_MANUF_NAME = UUID(0x02A29)
UUID_CHAR_MODEL_NUMBER = UUID(0x2A24)
UUID_CHAR_FIRM_REV = UUID(0x2A26)
UUID_SVC_CUSTOM = UUID(0xFFE0)
UUID_CHAR_CUSTOM = UUID(0xFFE1)


# asyncio tasks
async def blink_task():
    global ble_connected
    while True:
        if ble_connected:
            led.on()
        await aio.sleep_ms(100)
        led.off()
        await aio.sleep_ms(100)


async def ble_adv_task():
    global ble_connected
    while True:
        ble_connected = False
        connection = await aioble.advertise(interval_us=250_000, name='CustomPeriph',
                                            services=[UUID_SVC_DEV_INFO, UUID_SVC_CUSTOM])  # type: ignore
        ble_connected = True
        print(f'Connection from {connection.device}')
        await connection.disconnected()


async def char_update_task():
    while True:
        for i in range(0, 0x10_000):
            custom_char.write(i.to_bytes(2, 'big'), send_update=True)
            await aio.sleep_ms(10)


if __name__ == '__main__':
    # global vars
    ble_connected = False
    # I/O init
    led = Pin('LED', Pin.OUT)

    # init characteristics
    svc_dev_info = aioble.Service(UUID_SVC_DEV_INFO)
    aioble.Characteristic(svc_dev_info, UUID_CHAR_MANUF_NAME, read=True, initial='Acme')
    aioble.Characteristic(svc_dev_info, UUID_CHAR_MODEL_NUMBER, read=True, initial='model 1')
    aioble.Characteristic(svc_dev_info, UUID_CHAR_FIRM_REV, read=True, initial='0.1')
    svc_custom = aioble.Service(UUID_SVC_CUSTOM)
    custom_char = aioble.Characteristic(svc_custom, UUID_CHAR_CUSTOM, read=True, notify=True)
    aioble.register_services(svc_dev_info, svc_custom)

    # create asyncio task and run it
    loop = aio.get_event_loop()
    loop.create_task(ble_adv_task())
    loop.create_task(blink_task())
    loop.create_task(char_update_task())
    loop.run_forever()
