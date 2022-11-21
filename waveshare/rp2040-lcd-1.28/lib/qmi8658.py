"""
QMI8658 class

derived from original code at https://www.waveshare.com/wiki/RP2040-LCD-1.28#Demo

"""


class QMI8658:
    def __init__(self, i2c, addr=0x6b):
        self._bus = i2c
        self._address = addr
        # configure sensor
        self._apply_config()
        # sensor data
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.acc_z = 0.0
        self.gyr_x = 0.0
        self.gyr_y = 0.0
        self.gyr_z = 0.0

    def _read_byte(self,cmd):
        rec=self._bus.readfrom_mem(int(self._address),int(cmd),1)
        return rec[0]

    def _read_block(self, reg, length=1):
        rec=self._bus.readfrom_mem(int(self._address),int(reg),length)
        return rec

    def _read_u16(self,cmd):
        LSB = self._bus.readfrom_mem(int(self._address),int(cmd),1)
        MSB = self._bus.readfrom_mem(int(self._address),int(cmd)+1,1)
        return (MSB[0] << 8) + LSB[0]

    def _write_byte(self,cmd,val):
        self._bus.writeto_mem(int(self._address),int(cmd),bytes([int(val)]))

    def _apply_config(self):
        # REG CTRL1
        self._write_byte(0x02, 0x60)
        # REG CTRL2 : QMI8658AccRange_8g  and QMI8658AccOdr_1000Hz
        self._write_byte(0x03, 0x23)
        # REG CTRL3 : QMI8658GyrRange_512dps and QMI8658GyrOdr_1000Hz
        self._write_byte(0x04, 0x53)
        # REG CTRL4 : No
        self._write_byte(0x05, 0x00)
        # REG CTRL5 : Enable Gyroscope And Accelerometer Low-Pass Filter 
        self._write_byte(0x06, 0x11)
        # REG CTRL6 : Disables Motion on Demand.
        self._write_byte(0x07, 0x00)
        # REG CTRL7 : Enable Gyroscope And Accelerometer
        self._write_byte(0x08, 0x03)

    def _read_raw(self):
        xyz = [0] * 6
        raw_xyz = self._read_block(0x35, 12)
        for i in range(6):
            xyz[i] = (raw_xyz[(i*2)+1]<<8)|(raw_xyz[i*2])
            if xyz[i] >= 32767:
                xyz[i] = xyz[i]-65535
        return xyz

    def read(self):
        xyz = [0.0] * 6
        raw_xyz = self._read_raw()
        # QMI8658AccRange_8g
        acc_lsb_div = 1<<12
        # QMI8658GyrRange_512dps
        gyro_lsb_div = 64
        for i in range(3):
            xyz[i]=raw_xyz[i]/acc_lsb_div
            xyz[i+3]=raw_xyz[i+3]*1.0/gyro_lsb_div
        # upate sensor data
        self.acc_x = xyz[0]
        self.acc_y = xyz[1]
        self.acc_z = xyz[2]
        self.gyr_x = xyz[3]
        self.gyr_y = xyz[4]
        self.gyr_z = xyz[5]

    def who_am_i(self):
        return self._read_byte(0x00) == 0x05

    def read_rev(self):
        return self._read_byte(0x01)
