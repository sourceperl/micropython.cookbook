from machine import PWM


class Motor:
    def __init__(self, fwd_pin, bwd_pin) -> None:
        self._fwd_pwm = PWM(fwd_pin, duty_u16=0, freq=50)
        self._bwd_pwm = PWM(bwd_pin, duty_u16=0, freq=50)

    def backward(self, percent: int):
        self._fwd_pwm.duty_u16(0)
        self._bwd_pwm.duty_u16(0xffff * percent // 100)

    def forward(self, percent: int):
        self._bwd_pwm.duty_u16(0)
        self._fwd_pwm.duty_u16(0xffff * percent // 100)


class Servo:
    def __init__(self, pin, freq=50, min_us=500, max_us=2_500, min_degree=0, max_degree=180, debug=False, angle=180):
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
            print(f'{self}: set angle to {self.angle}° (pulse = {self.pulse_us} us)')

    def move(self, offset):
        self.angle += offset
