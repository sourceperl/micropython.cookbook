#
# Raspberry Pi Pico: basic micropython scheduler
#

from machine import I2C, Pin
import utime
from grove_lcd_rgb_i2c import Grove_LCD_RGB_I2C

# some const
I2C_ID = 0
I2C_SDA = 8
I2C_SCL = 9

# some vars
loop = 0

# init I2C bus
i2c = I2C(I2C_ID, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
# init LCD display
lcd = Grove_LCD_RGB_I2C(i2c)

# debug: scan I2C bus
#print('node(s) on I2C bus:', [hex(i) for i in i2c.scan()])

# turn on RGB backlight
lcd.setRGB(0x80, 0x80, 0x20)

# display the random number
lcd.clear()
lcd.cursor_position(col=0, row=0)
lcd.write('LOOP')
lcd.cursor_position(col=0, row=1)
lcd.write('TS')

# main loop
while True:
    loop += 1
    lcd.cursor_position(col=6, row=0)
    lcd.write('{:10d} '.format(loop))    
    lcd.cursor_position(col=4, row=1)
    lcd.write('{:12d} '.format(utime.time()))