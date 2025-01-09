import uasyncio as aio
import aioble


async def scan_task():
    # scan indefinitely
    async with aioble.scan(duration_ms=0, interval_us=30_000, window_us=30_000) as scanner:
        async for result in scanner:
            print(f'{result.name()}: {result.device=} {list(result.services())} {result.rssi} dBm')


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(scan_task())
loop.run_forever()
