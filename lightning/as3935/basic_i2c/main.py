"""
Test of AS3935 sensor with Cytron maker pi pico rev 1.2 board.
AS3935 is connect to grove port #1.
"""

from micropython import const
from machine import Pin, PWM, I2C
from utime import sleep_ms, localtime

# some const
AS_I2C_ADDR = const(0X03)
I2C_ID = const(0)
I2C_SDA_PIN = const(0)
I2C_SCL_PIN = const(1)
# AS special registers for commands
AS_CMD_PRESET_DEFAULT = const(0x3c)
AS_CMD_CALIB_RCO = const(0x3d)
AS_CMD_TRIG_VAL = const(0x96)
# AS registers address
AS_REG_0 = const(0x00)
AS_REG_1 = const(0x01)
AS_REG_2 = const(0x02)
AS_REG_3 = const(0x03)
AS_REG_8 = const(0x08)
# AS REG 0
# AFE gain boost, default = 0b10010
AS_AFE_GB = const(0b10010)
# power down, default (active)
AS_PWD = const(False)
# AS REG 1
# noise floor level, default = 0b010
AS_NF_LEV = const(0b010)
# watchdog threshold, default = 0b0010
AS_WDTH = const(0b0011)
# AS REG 2
# clear statistics, default = True
AS_CL_STAT = const(True)
# minimum number of lightning, default = 0b00
AS_MIN_NUM_LIGHT = const(0b00)
# spike rejection,default = 0b0010
AS_SREJ = const(0b0010)
# AS REG 3
# interrupt mask values
AS_INT_NOISE_HIGH = const(0x01)
AS_INT_DIST_DETECT = const(0x04)
AS_INT_LIGHTNING = const(0x08)
# REG 7
# lightning distance
AS_DIST_MASK = const(0x3f)
AS_DIST_OUT = const(0x3f)
# REG 8
# display LCO on IRQ pin (default=False)
AS_DISP_LCO = const(False)
# display SRCO on IRQ pin (default=False)
AS_DISP_SRCO = const(False)
# display TRCO on IRQ pin (default=False)
AS_DISP_TRCO = const(False)
# antenna tuning capacitance (must be integer multiple of 8, from 8 to 120 pf)
AS_CAP_PF = const(120)


# some functions
def log(msg: str):
    y, mo, d, h, mi, s = localtime()[:6]
    print(f'{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02} {msg}')


def beep():
    buzzer.duty_u16(19660)
    sleep_ms(200)
    buzzer.duty_u16(0)


def as_dump_regs():
    # dump config register
    print('dump of AS3935 registers:')
    for offset, value in enumerate(i2c.readfrom_mem(AS_I2C_ADDR, 0x00, 9)):
        print(f'reg 0x{offset + 0x00:02x} = _{value >> 4:04b}_{value & 0x0f:04b}_')
    for offset, value in enumerate(i2c.readfrom_mem(AS_I2C_ADDR, 0x3a, 2)):
        print(f'reg 0x{offset + 0x3a:02x} = _{value >> 4:04b}_{value & 0x0f:04b}_')


# IO init
buzzer = PWM(Pin(18))
buzzer.freq(440)
buzzer.duty_u16(0)

# I2C init
i2c = I2C(I2C_ID, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400_000)

# AS3935 send init command (see ams datasheet v1.04 page 23)
# set all registers to default values
i2c.writeto_mem(AS_I2C_ADDR, AS_CMD_PRESET_DEFAULT, bytes([AS_CMD_TRIG_VAL]))
# calibrates automatically the internal RC oscillators
i2c.writeto_mem(AS_I2C_ADDR, AS_CMD_CALIB_RCO, bytes([AS_CMD_TRIG_VAL]))
# customize default configuration with const values
reg = (AS_AFE_GB << 1) + AS_PWD
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_0, bytes([reg]))
reg = (AS_NF_LEV << 4) + AS_WDTH
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_1, bytes([reg]))
reg = (0b1 << 7) + (AS_CL_STAT << 6) + (AS_MIN_NUM_LIGHT << 4) + AS_SREJ
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_2, bytes([reg]))
reg = (AS_DISP_LCO << 7) + (AS_DISP_SRCO << 6) + (AS_DISP_TRCO << 5) + (AS_CAP_PF // 8)
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_8, bytes([reg]))

# buzzer test
print('test the buzzer at startup')
beep()

# dump config
print('')
as_dump_regs()

# main detection loop
print('')
print('run detection loop:')
while True:
    # read AS3935 interrupt status (flags will be reset after read)
    as_int_status = i2c.readfrom_mem(AS_I2C_ADDR, AS_REG_3, 1)[0]
    if as_int_status:
        print(f'as_int_status = 0x{as_int_status:02x}')
        light_km = i2c.readfrom_mem(AS_I2C_ADDR, 0x07, 1)[0]
        light_km &= AS_DIST_MASK
        if light_km == AS_DIST_OUT:
            log(f'distance is out of range')
        else:
            log(f'distance is {light_km} km')
        # as_dump_regs()
    # process status on need
    if as_int_status & AS_INT_LIGHTNING:
        log('lightning occur')
        # get distance
        light_km = i2c.readfrom_mem(AS_I2C_ADDR, 0x07, 1)[0]
        log(f'distance is {light_km} km')
        # get raw intensity
        energy_raw = int.from_bytes(i2c.readfrom_mem(AS_I2C_ADDR, 0x04, 3), 'little')
        log(f'raw energy is {energy_raw / 2 ** 21:0.2f} %')
        # sound alert
        beep()
    elif as_int_status & AS_INT_NOISE_HIGH:
        log('noise level too high')
    elif as_int_status & AS_INT_DIST_DETECT:
        log('disturber detected')
    # before next loop
    sleep_ms(10)
