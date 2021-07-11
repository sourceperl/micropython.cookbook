from machine import Pin, PWM
import uasyncio as aio


# some const
SRV_F_HZ = 100
SRV_POS_0_MS = 0.55
SRV_POS_180_MS = 2.37
SRV_DUTY_POS_0 = SRV_POS_0_MS/(1000/SRV_F_HZ)
SRV_DUTY_POS_180 = SRV_POS_180_MS/(1000/SRV_F_HZ)

# init I/O
led = Pin(25, Pin.OUT)
servo = PWM(Pin(16))
servo.freq(SRV_F_HZ)


# some functions
def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


# asyncio tasks
async def led_task():
    # main  loop
    while True:
        led.on()
        await aio.sleep_ms(100)
        led.off()
        await aio.sleep_ms(100)


async def main_task():
    while True:
        for angle in (0,45,90,135,180):
            duty = remap(angle, 0, 180, SRV_DUTY_POS_0, SRV_DUTY_POS_180)
            print('set to %d° (duty cycle %.2f %%)' % (angle, duty*100))
            servo.duty_u16(round(duty * 65535))
            await aio.sleep(4.0)


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(led_task())
loop.create_task(main_task())
loop.run_forever()
