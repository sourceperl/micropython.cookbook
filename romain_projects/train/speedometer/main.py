""" Test of lego train speedometer with tof sensors.

board: Maker Pi RP2040
version: MicroPython v1.22.2
"""

from time import ticks_ms, ticks_diff
from machine import Pin, I2C, PWM
# from https://github.com/stlehmann/micropython-ssd1306/
from lib.ssd1306 import SSD1306_I2C
# from https://github.com/kevinmcaleer/vl53l0x
from lib.vl53l0x import VL53L0X


# some const
SENSORS_DIST_M = 0.33


# I/O setup
led_0 = Pin(0)
led_1 = Pin(1)
# grove 4
i2c_0 = I2C(0, sda=Pin(16), scl=Pin(17))
tof_0 = VL53L0X(i2c_0)
# grove 6 (with I2C HUB)
i2c_1 = I2C(1, sda=Pin(26), scl=Pin(27))
tof_1 = VL53L0X(i2c_1)
oled = SSD1306_I2C(128, 32, i2c_1)
pwm_buz = PWM(Pin(22))


# main loop
last_trg_s0 = False
last_trg_s1 = False
t_trg_s0_ms = 0
t_trg_s1_ms = 0

while True:
    # sensors reading
    mm_s0 = tof_0.ping()
    mm_s1 = tof_1.ping()

    # set trigger flags
    trig_s0 = mm_s0 < 100
    trig_s1 = mm_s1 < 100

    # events detect
    if trig_s0 and not last_trg_s0:
        t_trg_s0_ms = ticks_ms()
    if trig_s1 and not last_trg_s1:
        t_trg_s1_ms = ticks_ms()
    last_trg_s0 = trig_s0
    last_trg_s1 = trig_s1
    diff_sensor_ms = ticks_diff(t_trg_s1_ms, t_trg_s0_ms)
    train_dir_1 = diff_sensor_ms > 0
    diff_sensor_ms = abs(diff_sensor_ms)

    # speed calculator
    try:
        diff_sensor_s = diff_sensor_ms / 1_000
        speed_train_ms = SENSORS_DIST_M/diff_sensor_s
        speed_train_kmh = round(3.6*speed_train_ms, 2)
    except ZeroDivisionError:
        speed_train_kmh = None

    # console message
    speed_train_str = 'n/a'
    if speed_train_kmh is not None:
        speed_train_str = f'{speed_train_kmh} km/h'

    c_msg = f'S0 :{mm_s0:>6} mm ({t_trg_s0_ms:>10} ms)\t'
    c_msg += f'S1 :{mm_s1:>6} mm ({t_trg_s1_ms:>10} ms) '
    c_msg += f'[dir_1={train_dir_1} diff={diff_sensor_ms:>10} ms, speed={speed_train_str:>10}]'
    print(c_msg, end='\r')

    # oled display
    dir_str = '>>>' if train_dir_1 else '<<<'
    oled_str_0 = f'{speed_train_str:^16}'
    oled_str_1 = f'{dir_str:^16}'
    # refresh screen
    oled.fill(0)
    oled.text(oled_str_0, 0, 5)
    oled.text(oled_str_1, 0, 15)
    oled.show()

    # LEDs
    led_0.value(trig_s1)
    led_1.value(trig_s1)

    # buzzer
    buzz_freq = 0
    if trig_s0 and trig_s1:
        buzz_freq = 1200
    elif trig_s0:
        buzz_freq = 440
    elif trig_s1:
        buzz_freq = 880

    if trig_s0 or trig_s1:
        pwm_buz.freq(buzz_freq)
        pwm_buz.duty_u16(0x7fff)
    else:
        pwm_buz.duty_u16(0)
