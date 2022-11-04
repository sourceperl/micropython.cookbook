from micropython import const
from ustruct import unpack


# some const
_RAM_TA = const(0x06)
_RAM_TOBJ1 = const(0x07)
_RAM_TOBJ2 = const(0x08)


# MLX90614 class access
class MLX90614:
    def __init__(self, i2c, addr=0x5a):
        self.i2c = i2c
        self.addr = addr

    def _i2c_read_16b(self, mem_addr):
        raw = self.i2c.readfrom_mem(self.addr, mem_addr, 2)
        return unpack('<H', raw)[0]

    @property
    def ambient_temp(self):
        return self._i2c_read_16b(_RAM_TA) * 0.02 - 273.15

    @property
    def object_temp(self):
        return self._i2c_read_16b(_RAM_TOBJ1) * 0.02 - 273.15

    @property
    def object2_temp(self):
        return self._i2c_read_16b(_RAM_TOBJ2) * 0.02 - 273.15
