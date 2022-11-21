"""
Test of Waveshare RP2040-LCD-1.28
"""


from machine import Pin, SPI, I2C
from micropython import const
from utime import sleep_ms
from urandom import randint, getrandbits
from lib.qmi8658 import QMI8658
# https://github.com/russhughes/gc9a01py
from lib.gc9a01py import GC9A01, color565
# choose a font
# from fonts.romfonts import vga1_8x8 as font
# from fonts.romfonts import vga2_8x8 as font
# from fonts.romfonts import vga1_8x16 as font
# from fonts.romfonts import vga2_8x16 as font
# from fonts.romfonts import vga1_16x16 as font
# from fonts.romfonts import vga1_bold_16x16 as font
# from fonts.romfonts import vga2_16x16 as font
# from fonts.romfonts import vga2_bold_16x16 as font
# from fonts.romfonts import vga1_16x32 as font
# from fonts.romfonts import vga1_bold_16x32 as font
# from fonts.romfonts import vga2_16x32 as font
from fonts.romfonts import vga2_bold_16x32 as font

# some const
TFT_DC = const(8)
TFT_ = const(9)
TFT_SCK = const(10)
TFT_MOSI = const(11)
TFT_RST = const(12)
TFT_BL = const(25)
IMU_I2C_ID = const(1)
IMU_I2C_SCL = const(7)
IMU_I2C_SDA = const(6)
IMU_I2C_FREQ = const(400_000)
IMU_I2C_ADDR= const(0x6b)

# init i2c bus for IMU
i2c= I2C(id=IMU_I2C_ID, scl=Pin(IMU_I2C_SCL), sda=Pin(IMU_I2C_SDA), freq=IMU_I2C_FREQ)
# init IMU sensor
imu = QMI8658(i2c, addr=IMU_I2C_ADDR)

# init SPI bus for LCD
spi = SPI(1, baudrate=60_000_000, sck=Pin(TFT_SCK), mosi=Pin(TFT_MOSI))
# init LCD display
tft = GC9A01(spi, dc=Pin(TFT_DC, Pin.OUT), cs=Pin(TFT_, Pin.OUT), reset=Pin(TFT_RST, Pin.OUT),
             backlight=Pin(TFT_BL, Pin.OUT), rotation=0)

# main loop
while True:
    # refresh LCD display
    for lcd_msg in ['Hello', ]:
        # read IMU
        imu.read()
        print(f'{imu.acc_x=:.3f}g {imu.acc_y=:.3f}g {imu.acc_z=:.3f}g')
        # fix LCD rotation with IMU
        if imu.acc_y < -0.5:
            tft.rotation(1)
        elif imu.acc_y > 0.5:
            tft.rotation(3)
        else:
            tft.rotation(0)
        # clean display
        tft.fill(0xff)
        col_max = tft.width - font.WIDTH * len(lcd_msg)
        row_max = tft.height - font.HEIGHT
        # draw text banners
        for _ in range(10):
            tft.text(font, lcd_msg, randint(0, col_max), randint(0, row_max),
                color565(getrandbits(8), getrandbits(8), getrandbits(8)),
                color565(getrandbits(8), getrandbits(8), getrandbits(8)),
            )
            sleep_ms(100)
