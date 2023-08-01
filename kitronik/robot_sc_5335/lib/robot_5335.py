"""Kitronik SC 5335 micropython library."""

from machine import ADC, Pin, PWM, time_pulse_us
from utime import sleep_us
from lib.neopixel import Neopixel


# some const
DEFAULT_PIX_MACHINE_ID = 0


# some class
class Colors:
    BLUE = (0, 0, 255)
    CYAN = (0, 255, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    YELLOW = (255, 150, 0)
    WHITE = (255, 255, 255)


class Button:
    def __init__(self, but_pin: Pin) -> None:
        self.but_pin = but_pin
        self.but_pin.irq(handler=self.on_press)

    def on_press(self, _pin):
        pass


class Motor:
    def __init__(self, fwd_pin: Pin, rev_pin: Pin) -> None:
        self.fwd_pin = fwd_pin
        self.rev_pin = rev_pin
        self.fwd_pwm = PWM(self.fwd_pin)
        self.rev_pwm = PWM(self.rev_pin)
        self.fwd_pwm.freq(100)
        self.rev_pwm.freq(100)

    def speed(self, speed: int):
        """Fix motor speed between 0 and 100 % (+=forward, -=reverse)"""
        # map absolute speed (0/100%) to PWM value (0/0xffff)
        pwm_value = abs(0xffff * speed // 100)
        # apply forward/reverse/stop PWM values to motor
        if speed > 0:
            self.rev_pwm.duty_u16(0)
            self.fwd_pwm.duty_u16(pwm_value)
        elif speed < 0:
            self.fwd_pwm.duty_u16(0)
            self.rev_pwm.duty_u16(pwm_value)
        else:
            self.fwd_pwm.duty_u16(0)
            self.rev_pwm.duty_u16(0)


class Robot:
    def __init__(self, pix_machine_id: int = DEFAULT_PIX_MACHINE_ID) -> None:
        # motors left and right
        self.motor_l = Motor(fwd_pin=Pin(20, Pin.OUT), rev_pin=Pin(19, Pin.OUT))
        self.motor_r = Motor(fwd_pin=Pin(6, Pin.OUT), rev_pin=Pin(7, Pin.OUT))
        # user button
        self.button = Button(but_pin=Pin(0, Pin.IN, Pin.PULL_DOWN))
        # buzzer
        self.buzzer_pin = Pin(16, Pin.OUT)
        self.buzzer_pwm = PWM(self.buzzer_pin)
        # front US sensor
        self.us_f_trig_pin = Pin(14, Pin.OUT)
        self.us_f_echo_pin = Pin(15, Pin.IN)
        # rear US sensor
        self.us_r_trig_pin = Pin(3, Pin.OUT)
        self.us_r_echo_pin = Pin(2, Pin.IN)
        # pixels (LEDs 1 to 4)
        self.pixs = Neopixel(num_leds=4, state_machine=pix_machine_id, pin=18, mode='GRB')
        # line follower sensors
        self.lf_right_adc = ADC(26)
        self.lf_center_adc = ADC(27)
        self.lf_left_adc = ADC(28)

    def buzzer_on(self, freq: int = 440):
        self.buzzer_pwm.freq(freq)
        self.buzzer_pwm.duty_u16(0x7fff)

    def buzzer_off(self):
        self.buzzer_pwm.duty_u16(0)

    def get_distance(self, rear: bool = False):
        """Read distance in cm from front (default) or rear US sensor"""
        # select US sensor
        trig_pin = self.us_r_trig_pin if rear else self.us_f_trig_pin
        echo_pin = self.us_r_echo_pin if rear else self.us_f_echo_pin
        # trig a new measure cycle
        trig_pin.low()
        sleep_us(2)
        trig_pin.high()
        sleep_us(5)
        trig_pin.low()
        # measure echo time (us) and convert it to distance (cm)
        echo_delay_us = time_pulse_us(echo_pin, 1, 29_154)
        if echo_delay_us > -1:
            return echo_delay_us * 0.0343 / 2
        else:
            return

    def get_lf_bright(self):
        """Get line follower sensors brigthness in percent. Return tuple (left value, center value, right value)"""
        adc_tuple = (self.lf_left_adc, self.lf_center_adc, self.lf_right_adc)
        return tuple(100.0 * (1.0 - (adc.read_u16()/0xffff)) for adc in adc_tuple)
