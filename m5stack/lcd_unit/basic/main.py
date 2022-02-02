import utime
from machine import I2C


# some class
class M5S_LCD:
    def __init__(self, i2c, address=0x3e):
        self.i2c = i2c
        self.address = address
        self.x_max = 135
        self.y_max = 240

    def send_cmd(self, cmd_bytes):
        self.i2c.writeto(self.address, cmd_bytes)

    def brightness(self, level=0xff):
        self.send_cmd(bytes((0x22, level)))

    def clear(self, clear_color=0x00):
        # fill all area with clear_color
        self.fill_rectangle(x_right=self.x_max, y_bottom=self.y_max, color=clear_color)

    def color_inv_off(self):
        self.send_cmd(b'\x20')

    def color_inv_on(self):
        self.send_cmd(b'\x21')

    def fill_rectangle(self, x_left=0, y_top=0, x_right=0, y_bottom=0, color=0x00):
        # fill rectangle area with color
        self.send_cmd(bytes((0x69, x_left, y_top, x_right, y_bottom, color)))

    def select_x_range(self, x_left=0, x_right=0):
        # set x range selection
        self.send_cmd(bytes((0x2a, x_left, x_right)))

    def select_y_range(self, y_top=0, y_bottom=0):
        # set y range selection
        self.send_cmd(bytes((0x2b, y_top, y_bottom)))

    def select_all(self):
        # select all screen space
        self.select_x_range(x_left=0, x_right=self.x_max)
        self.select_y_range(y_top=0, y_bottom=self.y_max)

    def write_raw_rgb888(self, raw_rgb888=b''):
        # fill range selection area with RGB888 values
        self.send_cmd(b'\x43' + raw_rgb888)


if __name__ == '__main__':
    # init
    i2c_1 = I2C(1)
    lcd = M5S_LCD(i2c_1)
    lcd.clear()
    utime.sleep(1.0)
    lcd.fill_rectangle(x_right=134, y_bottom=79, color=0x0e)
    lcd.fill_rectangle(x_right=134, y_top=80, y_bottom=159, color=0xff)
    lcd.fill_rectangle(x_right=134, y_top=160, y_bottom=240, color=0xe0)
