# Grove-LCD RGB Backlight 16x2 I2C class

from machine import Pin, I2C
from utime import sleep_ms, sleep_us


# some const
# I2C address
LCD_ADDR = 0x3e
RGB_ADDR = 0x62

# commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# flags for display entry mode
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# flags for display/cursor shift
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# flags for function set
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# PCA9685 registers (PWM RGB backlight control)
REG_MODE1 = 0x00
REG_MODE2 = 0x01
REG_OUTPUT = 0x08

REG_BLUE = 0x02
REG_GREEN = 0x03
REG_RED = 0x04


# some class
class Grove_LCD_RGB_I2C(object):
    def __init__(self, i2c, line=2, char_size=LCD_5x8DOTS):
        # public
        self.i2c = i2c
        # private
        self._disp_func = LCD_DISPLAYON | char_size | LCD_2LINE if line == 2 else LCD_1LINE
        self._disp_ctrl = LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF
        self._disp_mode = LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT

        # wait display init after power-on
        sleep_ms(50)

        # send function set
        self.cmd(LCD_FUNCTIONSET | self._disp_func)
        sleep_us(4500)
        self.cmd(LCD_FUNCTIONSET | self._disp_func)
        sleep_us(150)
        self.cmd(LCD_FUNCTIONSET | self._disp_func)
        self.cmd(LCD_FUNCTIONSET | self._disp_func)

        # turn on the display
        self.display(True)

        # clear it
        self.clear()

        # set default text direction (left-to-right)
        self.cmd(LCD_ENTRYMODESET | self._disp_mode)

        # init RGB backlight
        self.i2c.writeto_mem(RGB_ADDR, REG_MODE1, b'\x00')
        self.i2c.writeto_mem(RGB_ADDR, REG_MODE2, b'\x20')
        self.i2c.writeto_mem(RGB_ADDR, REG_OUTPUT, b'\xaa')

    # set backlight to (R,G,B) (values from 0..255 for each)
    def setRGB(self, r, g, b):
        self.i2c.writeto_mem(RGB_ADDR, REG_RED, bytes([r]))
        self.i2c.writeto_mem(RGB_ADDR, REG_GREEN, bytes([g]))
        self.i2c.writeto_mem(RGB_ADDR, REG_BLUE, bytes([b]))

    def cmd(self, command):
        assert command >= 0 and command < 256
        command = bytearray([command])
        self.i2c.writeto_mem(LCD_ADDR, 0x80, bytearray([]))
        self.i2c.writeto_mem(LCD_ADDR, 0x80, command)

    def write_char(self, char):
        self.i2c.writeto_mem(LCD_ADDR, 0x40, bytes([ord(char)]))

    def write(self, text):
        for char in text:
            if char == '\n':
                self.cursor_position(0, 1)
            else:
                self.write_char(char)

    def cursor(self, state):
        if state:
            self._disp_ctrl |= self.LCD_CURSORON
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)
        else:
            self._disp_ctrl &= ~self.LCD_CURSORON
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)

    def cursor_position(self, col, row):
        col = (col | 0x80) if row == 0 else (col | 0xc0)
        self.cmd(col)

    def autoscroll(self, state):
        if state:
            self._disp_ctrl |= LCD_ENTRYSHIFTINCREMENT
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)
        else:
            self._disp_ctrl &= ~LCD_ENTRYSHIFTINCREMENT
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)

    def blink(self, state):
        if state:
            self._disp_ctrl |= LCD_BLINKON
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)
        else:
            self._disp_ctrl &= ~LCD_BLINKON
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)

    def display(self, state):
        if state:
            self._disp_ctrl |= LCD_DISPLAYON
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)
        else:
            self._disp_ctrl &= ~LCD_DISPLAYON
            self.cmd(LCD_DISPLAYCONTROL  | self._disp_ctrl)

    def clear(self):
        self.cmd(LCD_CLEARDISPLAY)
        sleep_ms(2)

    def home(self):
        self.cmd(LCD_RETURNHOME)
        sleep_ms(2)
