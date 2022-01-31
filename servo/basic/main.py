from machine import Pin, PWM
import time


# some class
class Servo:
    def __init__(self, pin, freq=50, min_us=500, max_us=2500, degree=180):
        # private
        self._pwm = PWM(pin)
        self._pwm.freq(freq)
        self._angle = 0
        self._pulse_us = 0
        # public
        self.min_us = min_us
        self.max_us = max_us
        self.degree = degree

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
        self._angle = int(value)
        self.pulse_us = self.min_us + self._angle * (self.max_us - self.min_us) // self.degree

    @property
    def pulse_us(self):
        return self._pulse_us

    @pulse_us.setter
    def pulse_us(self, value):
        self._pulse_us = int(value)
        self._pwm.duty_u16(self._pulse_us * 0xffff // self.cycle_us)


# init I/O
servo_1 = Servo(Pin(17, Pin.OUT), degree=270)
servo_1.angle = 0
step = 1

# infinite loop
while True:
    # auto-reverse on both end
    if servo_1.angle <= 0:
        step = 1
    if servo_1.angle >= 270:
        step = -1
    # update servo postion and print result
    servo_1.angle += step
    print(f'set to {servo_1.angle:3d}° (pulse = {servo_1.pulse_us:4d} us)')
    # wait next set
    time.sleep(0.05)
