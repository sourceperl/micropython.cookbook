# Raspberry Pi Pico: modbus RTU monitor

from utime import time, ticks_ms, ticks_diff
from uasyncio import sleep_ms, get_event_loop
from machine import I2C, Pin, UART
from math import ceil
from grove_lcd_rgb_i2c import Grove_LCD_RGB_I2C
from modbus_utils import crc16, frame2hex, check_crc_ok

# some const
BAUDRATE = 9600

# some global vars
crc_good = 0
crc_error = 0

# init IO
led = Pin(25, Pin.OUT)
# init I2C
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400_000)
# init UART
#uart = machine.UART(0, BAUDRATE, tx=Pin(0), rx=Pin(1), bits=8, parity=None, stop=1)
uart = machine.UART(1, BAUDRATE, tx=Pin(4), rx=Pin(5), bits=8, parity=None, stop=1)
# init LCD display with RGB backlight on
lcd = Grove_LCD_RGB_I2C(i2c)
lcd.setRGB(0x80, 0x80, 0x20)


# asyncio tasks
async def led_task():
    # main  loop
    while True:
        led.on()
        await sleep_ms(100)
        led.off()
        await sleep_ms(100)


async def lcd_task():
    # always on screen message
    lcd.clear()
    lcd.cursor_position(col=0, row=0)
    lcd.write('CRC OK')
    lcd.cursor_position(col=0, row=1)
    lcd.write('CRC ERR')
    # main loop
    while True:
        lcd.cursor_position(col=8, row=0)
        lcd.write('{:8d}'.format(crc_good))    
        lcd.cursor_position(col=8, row=1)
        lcd.write('{:8d}'.format(crc_error))
        await sleep_ms(500)


def uart_task():
    # global var
    global crc_good, crc_error
    # flush buffer at startup
    uart.read(uart.any())
    # main loop
    while True:
        rx_b = bytearray()
        rx_t = ticks_ms()
        # modbus end of frame is rx silent greater than 3.5 * byte tx time
        eof_silent = ceil(max(1.2 * 3.5 * (1000/(BAUDRATE/10)), 10.0))
        # frame receive loop
        while True:
            # on data available
            if uart.any() > 0:
                # read data block with time of arrival
                rx_t = ticks_ms()
                rx_b.extend(uart.read(uart.any()))
                # limit buffer size to 256 bytes
                rx_b = rx_b[-256:]
            frame_end = ticks_diff(ticks_ms(), rx_t) > eof_silent
            # out of receive loop if data in buffer and end of frame occur 
            if frame_end and rx_b:
                break
            await sleep_ms(0)
        await sleep_ms(0)
        # check frame
        crc_ok = check_crc_ok(rx_b)
        if crc_ok:
            crc_status = 'OK'
            crc_good += 1
        else:
            crc_status = 'ERR'
            crc_error += 1
        # dump frame
        print('[size %3d/eof %2d ms/CRC %3s] %s' % (len(rx_b), eof_silent, crc_status, frame2hex(rx_b)))


# create asyncio task and run it
loop = get_event_loop()
loop.create_task(led_task())
loop.create_task(lcd_task())
loop.create_task(uart_task())
loop.run_forever()
