import _thread
from collections import deque
from machine import Pin, UART
from lib.cmd import Cmd
# from lib.modbus import ModbusFrame


# some const
VERSION = '0.0.1'


# some class
class SerialConf:
    # public
    eof_ms = 4
    # private
    _baudrate = 9600
    _parity = None
    _bits = 8
    _stop = 1

    @property
    def baudrate(self): 
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int):
        if 300 <= value <= 115_200:
            self._baudrate = value
            self.update_eof()
        else:
            raise ValueError('bad value for baudrate (allowed value between 300 and 115200)')

    @property
    def parity_as_str(self): 
        return {None: 'N', 0: 'E', 1: 'O'}[self._parity]

    @parity_as_str.setter
    def parity_as_str(self, value: str):
        try:
            self._parity = {'N': None, 'E': 0, 'O': 1}[value]
            self.update_eof()
        except KeyError:
            raise ValueError('bad value for parity (allowed values: N, E or O)')

    @property
    def parity_as_int(self):
        return self._parity

    @parity_as_int.setter
    def parity_as_int(self, value: int):
        if value in [None, 0, 1]:
            self._parity = value
            self.update_eof()
        else:
            raise ValueError('bad value for parity (allowed values: None, 0 or 1)')

    @property
    def bits(self): 
        return self._bits

    @property
    def stop(self): 
        return self._stop

    @stop.setter
    def stop(self, value: int):
        if value in [1, 2]:
            self._stop = value
            self.update_eof()
        else:
            raise ValueError('bad value for stop (allowed values: 1 and 2)')

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
        
    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, SerialConf):
            return (self._baudrate) == (obj._baudrate) and (self._bits) == (obj._bits) and \
                   (self._parity) == (obj._parity) and (self._stop) == (obj._stop) and \
                   (self.eof_ms) == (obj.eof_ms)
        return False

    def __str__(self) -> str:
        return f'{self.baudrate},{self.parity_as_str},{self.bits},{self.stop}'


class Share:
    lock = _thread.allocate_lock()
    # serial configuration
    spy_serial_cnf = SerialConf()
    # flags
    run = True
    # data
    raw = b''


class SpyCli(Cmd):
    intro = 'modbus spy tool (type help)'

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        self.serial_cnf = SerialConf()

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
            self.stdout.write(f'parity set to {self.serial_cnf.parity_as_str}\n')

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
                self.stdout.write(f'unable to set eof\n')
        else:
            self.stdout.write(f'eof set to {self.serial_cnf.eof_ms} ms\n')

    def help_eof(self):
        self.stdout.write('set the end of frame silent delay in ms (example: "eof 3")\n')

    def do_dump(self, _arg):
        with Share.lock:
            raw = Share.raw
        print(raw)

    def do_version(self, _arg):
        self.stdout.write(f'modbus spy tool {VERSION}\n')

    def help_version(self):
        self.stdout.write('show the current version\n')


def core0_task():
    """ start user cli on core0 """
    try:
        SpyCli().cmdloop()
    except KeyboardInterrupt:
        Share.run = False


def core1_task():
    """ start continuous spy job with UART on core1 """
    # task init
    UART_ID = 1
    TX_PIN = Pin(4, Pin.IN)
    RX_PIN = Pin(5, Pin.IN)
    # task loop
    while Share.run:
        # init UART
        with Share.lock:
            baudrate = Share.spy_serial_cnf.baudrate
            bits = Share.spy_serial_cnf.bits
            parity = Share.spy_serial_cnf.parity_as_int
            stop = Share.spy_serial_cnf.stop
            eof_ms = Share.spy_serial_cnf.eof_ms
        uart = UART(UART_ID, baudrate=baudrate, bits=bits, parity=parity, stop=stop,
                    tx=TX_PIN, rx=RX_PIN, rxbuf=256, timeout=0, timeout_char=eof_ms)
        # spy with UART
        while Share.run:
            # read frame
            recv_raw_f = uart.read(256)
            if recv_raw_f:
                break
        if recv_raw_f:
            with Share.lock:
                Share.raw = recv_raw_f
        # deinit UART
        uart.deinit()


if __name__ == '__main__':
    # launch 2nd and 1st core task
    print(_thread.start_new_thread(core1_task, ()))
    core0_task()
