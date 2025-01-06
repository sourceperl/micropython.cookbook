""" Use this script with android Bluefruit app to control a lego hypercar with the control pad.

https://www.lego.com/fr-fr/product/peugeot-9x8-24h-le-mans-hybrid-hypercar-42156?consent-modal=show
"""

from lib.ble_ctrl import BLE_CTRL
from lib.io import Motor, Servo
from machine import Pin

import bluetooth
import uasyncio as aio


async def ble_task():
    # main loop (exit with ctrl-c)
    while True:
        # do ble stuff
        ble_ctrl.update()
        # allow other tasks to run
        await aio.sleep_ms(50)


async def telemetry_task():
    i = 0
    while True:
        ble_ctrl.write(f'telemetry #{i} \n')
        i += 1
        # wait 1s before next loop
        await aio.sleep_ms(1_000)


# main pogram
if __name__ == '__main__':
    # I/O init
    # onboard led
    led = Pin('LED', Pin.OUT)
    # init steering column servo
    servo_st = Servo(pin=Pin(27), min_degree=-135, max_degree=+135, angle=0, debug=True)

    # init forward/backward motor command
    motor = Motor(fwd_pin=Pin(2), bwd_pin=Pin(3))

    # bluetooth init
    ble = bluetooth.BLE()
    ble_ctrl = BLE_CTRL(ble, name='LEGO_CAR')

    # buttons setup
    ble_ctrl.btn_pressed_hdl[1] = led.on
    ble_ctrl.btn_pressed_hdl[2] = led.off
    # ble_ctrl.btn_pressed_hdl[3] =
    # ble_ctrl.btn_pressed_hdl[4] =
    ble_ctrl.btn_pressed_hdl[5] = lambda: motor.forward(50)
    ble_ctrl.btn_pressed_hdl[6] = lambda: motor.backward(50)
    ble_ctrl.btn_pressed_hdl[7] = lambda: servo_st.move(+5)
    ble_ctrl.btn_pressed_hdl[8] = lambda: servo_st.move(-5)

    # create asyncio task and run it
    loop = aio.get_event_loop()
    loop.create_task(ble_task())
    loop.create_task(telemetry_task())
    try:
        loop.run_forever()
    except:
        # clean on exit
        ble_ctrl.close()
