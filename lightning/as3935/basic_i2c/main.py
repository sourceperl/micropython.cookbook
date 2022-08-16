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
# antenna tuning capacitance (must be integer multiple of 8, from 8 to 120 pf)
AS_CAP_PF = const(120)
AS_DISP_LCO = const(False)
AS_DISP_SRCO = const(False)
AS_DISP_TRCO = const(False)
AS_AFE_GB = const(0b10010)
AS_PWD = const(False)
AS_NF_LEV = const(0b010)
AS_WDTH = const(0b0100)
AS_INT_NOISE_HIGH = const(0x01)
AS_INT_DIST_DETECT = const(0x04)
AS_INT_LIGHTNING = const(0x08)
AS_CMD_PRESET_DEFAULT = const(0x3c)
AS_CMD_CALIB_RCO = const(0x3d)
AS_CMD_TRIG = const(0x96)
AS_REG_0 = const(0x00)
AS_REG_1 = const(0x01)
AS_REG_3 = const(0x03)
AS_REG_8 = const(0x08)


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
i2c.writeto_mem(AS_I2C_ADDR, AS_CMD_PRESET_DEFAULT, bytes([AS_CMD_TRIG]))
sleep_ms(2)
# calibrates automatically the internal RC oscillators
i2c.writeto_mem(AS_I2C_ADDR, AS_CMD_CALIB_RCO, bytes([AS_CMD_TRIG]))
sleep_ms(2)
# set noise floor level and watchdog threshold
# bits pattern: 0bRR-AFE_GB-PWD,
# default is: 0bRR_10010_0
reg_v = (AS_AFE_GB << 1) + AS_PWD
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_0, bytes([reg_v]))
sleep_ms(2)
# set noise floor level and watchdog threshold
# bits pattern: 0bR-NF_LEV-WDTH
# default is: 0bR_010_0010
reg_v = (AS_NF_LEV << 4) + AS_WDTH
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_1, bytes([reg_v]))
sleep_ms(2)
# set internal tunning capacitor (from 0 to 120pF in steps of 8pF)
# bits pattern: 0bDISP_LCO-DISP_SRCO-DISP_TRCO-R-TUN_CAP
# default is: 0b0_0_0_R_0000
reg_v = (AS_DISP_LCO << 7) + (AS_DISP_SRCO << 6) + (AS_DISP_TRCO << 5) + (AS_CAP_PF // 8)
i2c.writeto_mem(AS_I2C_ADDR, AS_REG_8, bytes([reg_v]))
sleep_ms(2)

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
        as_dump_regs()
        beep()
    # process status on need
    if as_int_status & AS_INT_LIGHTNING:
        log('lightning occur')
        # get distance
        light_km = i2c.readfrom_mem(AS_I2C_ADDR, 0x07, 1)[0]
        log(f'distance is {light_km} km')
        # get raw intensity
        energy_raw = int.from_bytes(i2c.readfrom_mem(AS_I2C_ADDR, 0x04, 3), 'little')
        log(f'raw energy is {energy_raw / 2 ** 21:0}')
        # sound alert
        # TODO set this
        # beep()
    elif as_int_status & AS_INT_NOISE_HIGH:
        log('noise level too high')
    elif as_int_status & AS_INT_DIST_DETECT:
        log('disturber detected')
    # before next loop
    sleep_ms(10)
