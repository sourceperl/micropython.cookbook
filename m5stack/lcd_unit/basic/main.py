import utime
from machine import I2C


# some class
class M5S_LCD:
    def __init__(self, i2c, address=0x3e):
        self.i2c = i2c
        self.address = address
        self.x_max = 135
        self.y_max = 240

    def send_cmd(self, cmd_bytes: bytes):
        """Send a command to ESP32 screen controller."""
        self.i2c.writeto(self.address, cmd_bytes)

    def brightness(self, lvl: int=0xff):
        """Set screen brightness from min to max (0 to 255)."""
        self.send_cmd(b'\x22' + lvl.to_bytes(1, 'big'))

    def clear(self, rgb332: int=0):
        """Clear all screen area. Default clear color can be set with rgb232 arg."""
        self.fill_rect_8(x_right=self.x_max, y_bottom=self.y_max, rgb332=rgb332)

    def color_inv_off(self):
        """Turn off color inversion."""
        self.send_cmd(b'\x20')

    def color_inv_on(self):
        """Turn on color inversion."""
        self.send_cmd(b'\x21')

    def draw_pixel(self, x_pos: int=0, y_pos: int=0):
        """Draw single dot. Use the drawing color that is stored."""
        self.send_cmd(bytes([0x60, x_pos, y_pos]))

    def draw_pixel_8(self, x_pos: int=0, y_pos: int=0, rgb332: int=0):
        """Draw single dot. RGB332 1 byte for drawing color specification."""
        self.send_cmd(bytes([0x61, x_pos, y_pos]) + rgb332.to_bytes(1, 'big'))

    def draw_pixel_16(self, x_pos: int=0, y_pos: int=0, rgb565: int=0):
        """Draw single dot. RGB565 2 bytes for drawing color specification."""
        self.send_cmd(bytes([0x61, x_pos, y_pos]) + rgb565.to_bytes(2, 'big'))

    def draw_pixel_24(self, x_pos: int=0, y_pos: int=0, rgb888: int=0):
        """Draw single dot. RGB888 3 bytes for drawing color specification."""
        self.send_cmd(bytes([0x62, x_pos, y_pos]) + rgb888.to_bytes(3, 'big'))

    def fill_rect(self, x_left: int=0, y_top: int=0, x_right: int=0, y_bottom: int=0):
        """Fill rectangle. Use the drawing color that is stored."""
        self.send_cmd(bytes([0x68, x_left, y_top, x_right, y_bottom]))

    def fill_rect_8(self, x_left: int=0, y_top: int=0, x_right: int=0, y_bottom: int=0, rgb332: int=0):
        """Fill rectangle. RGB332 1 byte for drawing color specification."""
        self.send_cmd(bytes([0x69, x_left, y_top, x_right, y_bottom]) + rgb332.to_bytes(1, 'big'))

    def fill_rect_16(self, x_left: int=0, y_top: int=0, x_right: int=0, y_bottom: int=0, rgb565: int=0):
        """Fill rectangle. RGB565 2 bytes for drawing color specification."""
        self.send_cmd(bytes([0x6a, x_left, y_top, x_right, y_bottom]) + rgb565.to_bytes(2, 'big'))

    def fill_rect_24(self, x_left: int=0, y_top: int=0, x_right: int=0, y_bottom: int=0, rgb888: int=0):
        """Fill rectangle. RGB888 3 bytes for drawing color specification."""
        self.send_cmd(bytes([0x6b, x_left, y_top, x_right, y_bottom]) + rgb888.to_bytes(3, 'big'))

    def select_all(self):
        """Set selection to all screen area."""
        self.select_x_range(x_left=0, x_right=self.x_max)
        self.select_y_range(y_top=0, y_bottom=self.y_max)

    def select_x_range(self, x_left: int=0, x_right: int=0):
        """X-direction range selection."""
        self.send_cmd(bytes([0x2a, x_left, x_right]))

    def select_y_range(self, y_top: int=0, y_bottom: int=0):
        """Y-direction range selection."""
        self.send_cmd(bytes([0x2b, y_top, y_bottom]))

    def set_color_8(self, rgb332: int):
        """Specify the drawing color with RGB332."""
        self.send_cmd(b'\x51' + rgb332.to_bytes(1, 'big'))

    def set_color_16(self, rgb565: int):
        """Specify the drawing color with RGB565."""
        self.send_cmd(b'\x52' + rgb565.to_bytes(2, 'big'))

    def set_color_24(self, rgb888: int):
        """Specify the drawing color with RGB888."""
        self.send_cmd(b'\x53' + rgb888.to_bytes(3, 'big'))

    def set_sleep(self, sleep: bool):
        """LCD panel sleep setting."""
        if sleep:
            self.send_cmd(b'\x39\x01')
        else:
            self.send_cmd(b'\x39\x00')
            self.send_cmd(b'\x39\x00')

    def write_raw_8(self, raw_rgb332: bytes):
        """Draw image RGB332."""
        self.send_cmd(b'\x41' + raw_rgb332)

    def write_raw_16(self, raw_rgb565: bytes):
        """Draw image RGB565."""
        self.send_cmd(b'\x42' + raw_rgb565)

    def write_raw_24(self, raw_rgb888: bytes):
        """Draw image RGB888."""
        self.send_cmd(b'\x43' + raw_rgb888)


if __name__ == '__main__':
    # init
    i2c_1 = I2C(1)
    lcd = M5S_LCD(i2c_1)
    lcd.clear()
    utime.sleep(1.0)
    lcd.fill_rect_8(x_right=134, y_bottom=79, rgb332=0x0e)
    lcd.fill_rect_8(x_right=134, y_top=80, y_bottom=159, rgb332=0xff)
    lcd.fill_rect_8(x_right=134, y_top=160, y_bottom=240, rgb332=0xe0)
