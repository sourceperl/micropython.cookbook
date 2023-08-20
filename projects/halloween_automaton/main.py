"""Lego automaton project "Halloween House".

platform: Cytron Maker Pi RP2040 with rp2040
"""

from machine import Pin, PWM
from neopixel import NeoPixel
import random
import uasyncio as aio
import utime
from lib.servo import Servo


# some class
class Flags:
    pir_active = False
    fire_anim_on = True
    storm_anim_on = False
    char_is_show = False
    play_melody = False


# define async tasks
# main animation logic
async def logic_anim_task():
    while True:
        if Flags.char_is_show:
            Flags.storm_anim_on = True
        else:
            Flags.storm_anim_on = False
        # wait next step
        await aio.sleep_ms(100)


# lighning animation
async def storm_anim_task():
    while True:
        if Flags.storm_anim_on:
            # lightning series with one or more flash
            for _ in range(random.choice([1, 2, 4])):
                # lightning as LED flash
                storm_pix.fill((0xff, 0xff, 0xff))
                storm_pix.write()
                await aio.sleep_ms(10)
                storm_pix.fill((0x00, 0x00, 0x00))
                storm_pix.write()
                await aio.sleep_ms(random.randint(50, 400))
        # wait for next lightning series
        await aio.sleep_ms(random.randint(1_500, 5_000))


# fire animation
async def fire_anim_task():
    fire_color_t = (0xff, 0x66, 0x00)
    color_fade_by = 12
    while True:
        if Flags.fire_anim_on:
            # apply fire color to a random LED
            fire_pix[random.randint(0, len(fire_pix)-1)] = fire_color_t
            # fade down all LEDs
            for idx in range(len(fire_pix)):
                fire_pix[idx] = [min(max(color-color_fade_by, 0), 255) for color in fire_pix[idx]]
            fire_pix.write()
        else:
            fire_pix.fill((0x00, 0x00, 0x00))
            fire_pix.write()
        # wait for next refresh
        await aio.sleep_ms(20)


# servo animation
async def servo_anim_task():
    while True:
        # dismiss character
        # set servo postion
        sv_char.angle = 214
        Flags.char_is_show = False
        # print(f'set to {servo_1.angle:3d} deg (pulse = {servo_1.pulse_us:4d} us)')
        # wait next step
        await aio.sleep_ms(6_000)
        # show character
        # update servo postion
        sv_char.angle = 48
        # give the servo some time to move
        await aio.sleep_ms(300)
        Flags.char_is_show = True
        # wait next step
        await aio.sleep_ms(10_000)


# manage device active state from PIR sensor status (idle if no PIR trigger since 2 mn)
async def pir_sensor_task():
    pir_trig_ms = None
    while True:
        if pir_pin.value():
            pir_trig_ms = utime.ticks_ms()
        if pir_trig_ms is not None:
            Flags.pir_active = utime.ticks_ms() - pir_trig_ms < 120_000
        await aio.sleep_ms(1_000)


# play some sound with onboard piezo
async def melody_task():
    notes = {'c': 261, # do
             'd': 294, # re
             'e': 329, # mi
             'f': 349, # fa
             'g': 392, # sol
             'a': 440, # la
             'b': 493, # si
             'C': 523  # do
             }
    melody = 'c2,c,d3,c3,f3,e3,c2,c,d3,c3,g3,f3,8'
    while True:
        if Flags.play_melody:
            for mel_code in melody.split(','):
                # default
                freq, delay_ms = None, 100
                # convert every char (token) to freq (alpha) or delay value (digit * 100 ms)
                for token in mel_code:
                    if token.isalpha():
                        try:
                            freq = notes[token]
                        except IndexError:
                            pass
                    elif token.isdigit():
                        delay_ms = int(token) * 100
                # set freq or silence
                if freq is not None:
                    piezo.freq(freq)
                    piezo.duty_u16(0xffff//2)
                else:
                    piezo.duty_u16(0)
                # wait fo rnext melody code
                await aio.sleep_ms(delay_ms)
        # wait 200ms before next play_melody flag test
        await aio.sleep_ms(200)


# main pogram
if __name__ == '__main__':
    # init I/O
    piezo_pin = Pin(22, Pin.OUT)
    pir_pin = Pin(17, Pin.IN)
    sv_char_pin = Pin(12, Pin.OUT)
    fire_pix_pin = Pin(2, Pin.OUT)
    storm_pix_pin = Pin(26, Pin.OUT)
    # init servo
    sv_char = Servo(sv_char_pin, degree=270)
    sv_char.angle = 0
    # init piezo
    piezo = PWM(piezo_pin)
    # init pixels for led effects
    fire_pix = NeoPixel(pin=fire_pix_pin, n=9)
    storm_pix = NeoPixel(pin=storm_pix_pin, n=6)
    # create asyncio task and run it
    loop = aio.get_event_loop()
    loop.create_task(logic_anim_task())
    loop.create_task(pir_sensor_task())
    loop.create_task(storm_anim_task())
    loop.create_task(fire_anim_task())
    loop.create_task(servo_anim_task())
    loop.create_task(melody_task())
    loop.run_forever()
