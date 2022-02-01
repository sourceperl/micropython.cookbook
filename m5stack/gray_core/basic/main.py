import time
import random
from machine import Pin, SPI, I2C
from micropython import const
from ili934xnew import ILI9341, color565
import fonts.tt24 as tt24


# some const
BUTTON_A_PIN = const(39)
BUTTON_B_PIN = const(38)
BUTTON_C_PIN = const(37)
SPEAKER_PIN = const(25)

TFT_LED_PIN = const(32)
TFT_DC_PIN = const(27)
TFT_CS_PIN = const(14)
TFT_MOSI_PIN = const(23)
TFT_CLK_PIN = const(18)
TFT_RST_PIN = const(33)
TFT_MISO_PIN = const(19)

MPU9250_SCL_PIN = const(22)
MPU9250_SDA_PIN = const(21)


# some vars
key_a = Pin(BUTTON_A_PIN, Pin.IN)
key_b = Pin(BUTTON_B_PIN, Pin.IN)
key_c = Pin(BUTTON_C_PIN, Pin.IN)

# init spi
spi = SPI(2, baudrate=40000000, miso=Pin(TFT_MISO_PIN), 
          mosi=Pin(TFT_MOSI_PIN), sck=Pin(TFT_CLK_PIN))

# init display
tft_power = Pin(TFT_LED_PIN, Pin.OUT)
tft_power.value(1)
display = ILI9341(spi, cs=Pin(TFT_CS_PIN), dc=Pin(TFT_DC_PIN),
                  rst=Pin(TFT_RST_PIN), w=240,h=320, r=6, font=tt24)
display.erase()
display.set_pos(0,0)

c = 0
while True:
    # on key a press, reset counter
    if key_a.value() == 0:
        c = 0
    else:
        c += 1
    display.set_pos(0,0)
    display.print('compteur = %i' % c)
    time.sleep(1.0)
