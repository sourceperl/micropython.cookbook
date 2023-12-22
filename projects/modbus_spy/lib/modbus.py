import struct


# some class
class ModbusFrame:

    def __init__(self, raw: bytes=b'') -> None:
        self.raw = raw

    def __repr__(self) -> str:
        return self.as_hex

    def __len__(self) -> int:
        return len(self.raw)

    @property
    def raw_pdu(self) -> bytes:
        return self.raw[1:-2]

    @property
    def slave_address(self) -> int:
        return self.raw[0]

    @property
    def function_code(self) -> int:
        return self.raw[1]

    @property
    def is_valid(self) -> bool:
        return len(self.raw) > 4 and self.crc_is_valid

    @property
    def raw_without_crc(self) -> bytes:
        return self.raw[:-2]

    @property
    def raw_crc(self) -> bytes:
        return self.raw[-2:]

    @property
    def crc_compute(self) -> int:
        return self.crc16(self.raw_without_crc)

    @property
    def crc_decode(self) -> int:
        try:
            return struct.unpack('<H', self.raw_crc)[0]
        except ValueError:
            return

    @property
    def crc_is_valid(self) -> bool:
        return self.crc_decode == self.crc_compute

    @property
    def as_hex(self) -> str:
        return '-'.join(['%02X' % x for x in self.raw])

    @staticmethod
    def crc16(frame: bytes) -> int:
        crc = 0xFFFF
        for byte in frame:
            crc ^= byte
            for _ in range(8):
                lsb = crc & 1
                crc >>= 1
                if lsb:
                    crc ^= 0xA001
        return crc
