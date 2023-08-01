"""
Test of kitronik SC 5335 robot with micropython and asyncio.

Product: https://www.kitronik.co.uk/5335
Official lib: https://github.com/KitronikLtd/Kitronik-Pico-Autonomous-Robotics-Platform-MicroPython
"""

import rp2
import uasyncio as aio
from lib.robot_5335 import Colors, Robot


# some const
PIX_MACHINE_ID = 0


# define tasks
async def prox_task():
    """Proximity task"""
    global f_dist_cm
    while True:
        # read distance, update global var if success
        _f_dist_cm = robot.get_distance()
        if _f_dist_cm is not None:
            f_dist_cm = _f_dist_cm
            # update status with LEDs and buzzer
            if f_dist_cm < 30:
                robot.pixs.fill(Colors.RED)
                robot.buzzer_on(freq=880)
            elif f_dist_cm < 60:
                robot.pixs.fill(Colors.YELLOW)
                robot.buzzer_on(freq=440)
            else:
                robot.pixs.fill(Colors.GREEN)
                robot.buzzer_off()
            robot.pixs.show()
        await aio.sleep_ms(100)


async def move_task():
    """Moves task"""
    global f_dist_cm
    while True:
        if f_dist_cm < 20:
            robot.motor_r.speed(-20)
            robot.motor_l.speed(-20)
            await aio.sleep_ms(800)
        elif f_dist_cm < 45:
            robot.motor_r.speed(15)
            robot.motor_l.speed(-15)
        elif f_dist_cm < 60:
            robot.motor_r.speed(35)
            robot.motor_l.speed(15)
        else:
            robot.motor_r.speed(30)
            robot.motor_l.speed(30)
        await aio.sleep_ms(100)


def at_exit():
    # stop motors
    robot.motor_r.speed(0)
    robot.motor_l.speed(0)


if __name__ == '__main__':
    # ensure program is remove from state machine on rerun (avoid OSError: ENOMEM)
    rp2.PIO(PIX_MACHINE_ID).remove_program()
    # global vars
    f_dist_cm = 0
    # init robot
    robot = Robot(pix_machine_id=PIX_MACHINE_ID)
    robot.pixs.brightness(255//10)
    # create asyncio task and run it
    loop = aio.get_event_loop()
    loop.create_task(prox_task())
    loop.create_task(move_task())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        at_exit()
