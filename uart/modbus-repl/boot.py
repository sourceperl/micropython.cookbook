import struct
from time import ticks_add, ticks_diff, ticks_ms
from machine import Pin, UART


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
            return None

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


class Spy:
    UART_ID = 1
    TX_PIN = Pin(4, Pin.IN)
    RX_PIN = Pin(5, Pin.IN)

    def __init__(self, baudrate=9600, parity=None, stop=1, eof_ms=None):
        # public
        self.frames_l = []
        # private
        self._baudrate = None
        self._parity = None
        self._stop = None
        self._eof_ms = None
        # args to properties
        self.baudrate = baudrate
        self.parity = parity
        self.stop = stop
        self.eof_ms = eof_ms

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int):
        if not (300 <= value <= 115_200):
            raise ValueError('valid baudrate is between 300 to 115200 bauds')
        self._baudrate = int(value)

    @property
    def parity(self) -> int:
        return self._parity

    @parity.setter
    def parity(self, value: int):
        if value not in (None, 0, 1):
            raise ValueError('parity can be None, 0 (even) or 1 (odd)')
        self._parity = value

    @property
    def stop(self) -> int:
        return self._stop

    @stop.setter
    def stop(self, value: int):
        if value not in (1, 2):
            raise ValueError('stop (number of stop bits) can be 1 or 2')
        self._stop = int(value)

    @property
    def eof_ms(self) -> int:
        if self._eof_ms is None:
            # automatic
            # end of frame (eof) is a silence on rx line > 3.5 * byte transmit time
            _eof_ms = round(3.5 * (1000/(self.baudrate/11)))
            return max(_eof_ms, 1)
        else:
            return self._eof_ms

    @eof_ms.setter
    def eof_ms(self, value: int):
        if value is None:
            # automatic
            self._eof_ms = value
        else:
            # manual override
            if not (0 <= int(value) <= 1000):
                raise ValueError('eof_ms must be between 0 to 1000 ms or None (automatic)')
            self._eof_ms = int(value)

    def dump(self, size: int=10, wait_s: float=60.0):
        # check params
        size = int(size)
        if not (1 <= size <= 100):
            raise ValueError('size must be between 1 to 100')
        wait_s = float(wait_s)
        if not (1.0 <= wait_s <= 3600.0):
            raise ValueError('wait_s must be between 1 to 3600 s')
        print(f'end of frame detection set {self.eof_ms:d} ms (can be overide by "eof_ms" property)\n')
        # init UART
        uart = UART(self.UART_ID, baudrate=self.baudrate, bits=8, parity=self.parity, stop=self.stop,
                    tx=self.TX_PIN, rx=self.RX_PIN, rxbuf=256, timeout=0, timeout_char=self.eof_ms)
        # display analysis start message and a progress bar
        print('serial analysis in progress, please wait\n')
        print('[%s]' % ('-' * size), end='\r')
        print('[', end='')
        # init frame buffer
        self.frames_l.clear()
        # init loop values
        t_start_ms = ticks_ms()
        t_end_ms = ticks_add(t_start_ms, round(wait_s * 1000))
        skip_first = True
        try:
            # main loop
            while True:
                # frame receive loop
                while True:
                    # check timeout
                    if ticks_diff(ticks_ms(), t_end_ms) > 0:
                        raise RuntimeError('timeout error')
                    # read frame
                    recv_raw_f = uart.read(256)
                    if recv_raw_f:
                        break
                # skip the first frame
                if skip_first:
                    skip_first = False
                    continue
                # store receive f
                print('#', end='')
                self.frames_l.append(ModbusFrame(recv_raw_f))
                # exit on buffer full
                if len(self.frames_l) >= size:
                    break
            print('\n')
            # display the report
            print('synthesis report')
            print('')
            for i, frame in enumerate(self.frames_l):
                # format dump message
                crc_str = ('ERR', 'OK')[frame.crc_is_valid]
                # print dump message
                print(f'[{i:>3d}/{len(frame):>3}/{crc_str:<3}] {frame}')
            print('\nframes are also available in frames_l property')
        except RuntimeError as e:
            print(f'aborted: {e}')

    @staticmethod
    def help():
        print(open('help.txt', 'r').read())


# user uart
spy = Spy(baudrate=9600)
