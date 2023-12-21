import _thread
from collections import namedtuple
from machine import Pin, UART
from lib.cmd import Cmd
from lib.modbus import ModbusFrame


# some const
VERSION = '0.0.1'
FRAMES_BUF_SIZE = 100


# some class
class ThreadFlag:
    def __init__(self) -> None:
        self._lock = _thread.allocate_lock()

    def set(self):
        if not self._lock.locked():
            self._lock.acquire()

    def unset(self):
        if self._lock.locked():
            self._lock.release()

    def is_set(self):
        return self._lock.locked()


SerialParams = namedtuple('SerialParams', ('baudrate', 'parity', 'bits', 'stop', 'eof_ms'))


class SpyFlags:
    job_exit = ThreadFlag()
    job_reload = ThreadFlag()


class SpyConf:
    lock = _thread.allocate_lock()
    serial = SerialParams(9600, None, 8, 1, 1)


class SpyData:
    lock = _thread.allocate_lock()
    frames_l = []


class SerialConf:
    def __init__(self):
        # private
        self._baudrate = 9600
        self._parity = None
        self._bits = 8
        self._stop = 1
        self._eof_ms = 4

    @property
    def baudrate(self):
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int):
        if not 300 <= value <= 115_200:
            raise ValueError
        self._baudrate = value
        self.update_eof()
        self.on_change()

    @property
    def parity_as_str(self):
        return {None: 'N', 0: 'E', 1: 'O'}[self._parity]

    @parity_as_str.setter
    def parity_as_str(self, value: str):
        try:
            self._parity = {'N': None, 'E': 0, 'O': 1}[value]
            self.update_eof()
            self.on_change()
        except KeyError:
            raise ValueError

    @property
    def parity_as_int(self):
        return self._parity

    @parity_as_int.setter
    def parity_as_int(self, value: int):
        if value not in [None, 0, 1]:
            raise ValueError
        self._parity = value
        self.update_eof()
        self.on_change()

    @property
    def bits(self):
        return self._bits

    @property
    def stop(self):
        return self._stop

    @stop.setter
    def stop(self, value: int):
        if value not in [1, 2]:
            raise ValueError
        self._stop = value
        self.update_eof()
        self.on_change()

    @property
    def eof_ms(self):
        return self._eof_ms

    @eof_ms.setter
    def eof_ms(self, value: int):
        if not 0 < value < 1000:
            raise ValueError
        self._eof_ms = value
        self.on_change()

    @property
    def as_namedtuple(self):
        return SerialParams(self.baudrate, self.parity_as_int, self.bits, self.stop, self.eof_ms)

    def update_eof(self):
        # automatic update of end of frame (eof) delay
        # it's a silence on rx line > 3.5 * byte transmit time
        byte_len = 10 + self._stop
        if self._parity is not None:
            byte_len += 1
        byte_tx_ms = 1000 * byte_len / self._baudrate
        self.eof_ms = max(round(3.5 * byte_tx_ms), 1)

    def on_change(self):
        pass

    def __str__(self) -> str:
        return f'{self.baudrate},{self.parity_as_str},{self.bits},{self.stop}'


class SpyCli(Cmd):
    intro = 'modbus spy tool (type help)'

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        self.serial_cnf = SerialConf()
        self.serial_cnf.on_change = self.on_serial_change

    def on_serial_change(self):
        print("call on_serial_change()")
        # load new serial conf
        with SpyConf.lock:
            SpyConf.serial = self.serial_cnf.as_namedtuple
        # notify spy job to reload serial conf
        SpyFlags.job_reload.set()

    @property
    def prompt(self):
        return f'{self.serial_cnf}> '

    def emptyline(self):
        # on empty line do nothing (default behaviour repeat last cmd)
        return False

    def do_baudrate(self, arg: str):
        if arg:
            try:
                self.serial_cnf.baudrate = int(arg)
                self.stdout.write(f'baudrate set to {self.serial_cnf.baudrate} bauds\n')
            except ValueError:
                self.stdout.write(f'unable to set baudrate\n')
        else:
            self.stdout.write(f'baudrate set to {self.serial_cnf.baudrate} bauds\n')

    def help_baudrate(self):
        self.stdout.write('set the baudrate of the spied line (example: "baudrate 115200")\n')

    def do_parity(self, arg: str):
        if arg:
            try:
                self.serial_cnf.parity_as_str = arg.strip().upper()
            except ValueError:
                self.stdout.write(f'unable to set parity\n')
        else:
            self.stdout.write(
                f'parity set to {self.serial_cnf.parity_as_str}\n')

    def help_parity(self):
        self.stdout.write('set the parity to N, E or O (example: "parity E")\n')

    def do_stop(self, arg: str):
        if arg:
            try:
                self.serial_cnf.stop = int(arg.strip())
            except ValueError:
                self.stdout.write(f'unable to set the number of stop bit(s) (allowed values: 1 or 2)\n')
        else:
            self.stdout.write(f'number of stop bit(s) set to {self.serial_cnf.stop}\n')

    def help_stop(self):
        self.stdout.write('set the number of stop bit(s) (example: "stop 1")\n')

    def do_eof(self, arg: str):
        if arg:
            try:
                self.serial_cnf.eof_ms = int(arg.strip().upper())
            except ValueError:
                self.stdout.write(f'unable to set eof (valid between 1 and 999 ms\n')
        else:
            self.stdout.write(f'eof set to {self.serial_cnf.eof_ms} ms\n')

    def help_eof(self):
        self.stdout.write('set the end of frame silent delay in ms (example: "eof 3")\n')

    def do_dump(self, _arg):
        with SpyData.lock:
            dump_l = SpyData.frames_l.copy()
        for idx, frame in enumerate(dump_l):
            # format dump message
            crc_str = ('ERR', 'OK')[frame.crc_is_valid]
            # print dump message
            print(f'[{idx:>3d}/{len(frame):>3}/{crc_str:<3}] {frame}')

    def help_dump(self):
        self.stdout.write('show an hex dump of all receive frames\n')

    def do_version(self, _arg):
        self.stdout.write(f'modbus spy tool {VERSION}\n')

    def help_version(self):
        self.stdout.write('show the current version\n')

    def help_help(self):
        self.stdout.write('show help message about available commands\n')

    def do_start(self, _arg):
        with SpyConf.lock:
            SpyConf.serial = self.serial_cnf.as_namedtuple


def core0_task():
    """ start user cli on core0 """
    try:
        SpyCli().cmdloop()
    except KeyboardInterrupt:
        SpyFlags.job_exit.set()


def core1_task():
    """ start continuous spy job on core1 """
    # task init
    UART_ID = 1
    TX_PIN = Pin(4, Pin.IN)
    RX_PIN = Pin(5, Pin.IN)
    # task loop
    while True:
        # reset reload flag
        SpyFlags.job_reload.unset()
        # load UART conf
        with SpyConf.lock:
            uart = UART(UART_ID, tx=TX_PIN, rx=RX_PIN,
                        baudrate=SpyConf.serial.baudrate,
                        bits=SpyConf.serial.bits,
                        parity=SpyConf.serial.parity,
                        stop=SpyConf.serial.stop,
                        timeout_char=SpyConf.serial.eof_ms,
                        rxbuf=256, timeout=0)
        # frame recv loop
        while True:
            # try to read at max 256 bytes, return when timeout_char expire
            recv_frame = uart.read(256)
            # when frame is set
            if recv_frame:
                with SpyData.lock:
                    if len(SpyData.frames_l) >= FRAMES_BUF_SIZE:
                        SpyData.frames_l.pop(0)
                    SpyData.frames_l.append(ModbusFrame(recv_frame))
            # exit recv loop on job exit or reload request
            if SpyFlags.job_exit.is_set() or SpyFlags.job_reload.is_set():
                break
        # deinit UART
        uart.deinit()
        # exit on request (avoid OSError: core1 in use )
        if SpyFlags.job_exit.is_set():
            break


if __name__ == '__main__':
    # launch 2nd and 1st core task
    _thread.start_new_thread(core1_task, ())
    core0_task()
