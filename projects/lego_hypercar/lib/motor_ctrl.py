from machine import Pin, PWM


class Motor:
    def __init__(self, fwd_pin: Pin, bwd_pin: Pin, debug: bool = False) -> None:
        # args
        self.fwd_pin = fwd_pin
        self.bwd_pin = bwd_pin
        self.debug = debug
        # init pwm
        self._fwd_pwm = PWM(fwd_pin, duty_u16=0, freq=50)
        self._bwd_pwm = PWM(bwd_pin, duty_u16=0, freq=50)
        # private vars
        self._speed = 0
        self._set_pwm()

    @property
    def speed(self) -> int:
        return self._speed

    @speed.setter
    def speed(self, value):
        if -100 <= value <= 100:
            self._speed = value
            self._set_pwm()

    def adjust(self, offset: int):
        self.speed += offset

    def _set_pwm(self):
        if self.debug:
            print(f'{self}: adjust speed to {self.speed} %')
        pwm_val = 0xffff * abs(self._speed) // 100
        if self._speed >= 0:
            self._bwd_pwm.duty_u16(0)
            self._fwd_pwm.duty_u16(pwm_val)
        else:
            self._fwd_pwm.duty_u16(0)
            self._bwd_pwm.duty_u16(pwm_val)


class Servo:
    def __init__(self, pin: Pin, freq: int = 50, min_us: int = 500, max_us: int = 2_500,
                 min_degree: int = 0, max_degree: int = 180, debug: bool = False, angle: int = 180):
        # private
        self._pwm = PWM(pin)
        self._pwm.freq(freq)
        self._angle = 0
        self._pulse_us = 0
        # public
        self.min_us = min_us
        self.max_us = max_us
        self.min_degree = min_degree
        self.max_degree = max_degree
        self.debug = debug
        self.angle = angle

    @property
    def freq(self):
        return self._pwm.freq()

    @property
    def cycle_us(self):
        return 1_000_000//self.freq

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = max(min(value, self.max_degree), self.min_degree)
        ratio = (self._angle - self.min_degree) / (self.max_degree - self.min_degree)
        self.pulse_us = self.min_us + (self.max_us - self.min_us) * ratio

    @property
    def pulse_us(self):
        return self._pulse_us

    @pulse_us.setter
    def pulse_us(self, value):
        self._pulse_us = int(value)
        self._pwm.duty_u16(self._pulse_us * 0xffff // self.cycle_us)
        if self.debug:
            print(f'{self}: set angle to {self.angle} degree (pulse = {self.pulse_us} us)')

    def adjust(self, offset):
        self.angle += offset
