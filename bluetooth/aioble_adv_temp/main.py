import uasyncio as aio
import aioble
from bluetooth import UUID

# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = UUID(0x181A)


# wait for connections (don't advertise while a central is connected)
async def adv_task():
    while True:
        await aioble.advertise(interval_us=250_000, connectable=False, name='mpy-temp',
                               services=(_ENV_SENSE_UUID, ), manufacturer=(0x1455, b'\xff\xff'))


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(adv_task())
loop.run_forever()
