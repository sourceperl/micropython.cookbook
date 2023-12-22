import _thread
from machine import Pin, UART
from lib.cmd import Cmd
from lib.misc import ThreadFlag
from lib.modbus import ModbusFrame


# some const
VERSION = '0.0.1'
FRAMES_BUF_SIZE = 100
UART_ID = 1
UART_TX = Pin(4, Pin.IN)
UART_RX = Pin(5, Pin.IN)


# some class
class SerialConf:
    class Params:
        def __init__(self) -> None:
            self.baudrate: int = 9600
            self.parity: int = None
            self.bits: int = 8
            self.stop = 1
            self.eof_ms: int = 4

    def __init__(self):
        # private
        self._params = self.Params()

    @property
    def params(self):
        return self._params

    @property
    def baudrate(self):
        return self._params.baudrate

    @baudrate.setter
    def baudrate(self, value: int):
        if not 300 <= value <= 115_200:
            raise ValueError
        self._params.baudrate = value
        self.update_eof()
        self.on_change()

    @property
    def parity_as_str(self):
        return {None: 'N', 0: 'E', 1: 'O'}[self._params.parity]

    @parity_as_str.setter
    def parity_as_str(self, value: str):
        try:
            self._params.parity = {'N': None, 'E': 0, 'O': 1}[value]
            self.update_eof()
            self.on_change()
        except KeyError:
            raise ValueError

    @property
    def parity_as_int(self):
        return self._params.parity

    @parity_as_int.setter
    def parity_as_int(self, value: int):
        if value not in [None, 0, 1]:
            raise ValueError
        self._params.parity = value
        self.update_eof()
        self.on_change()

    @property
    def bits(self):
        return self._params.bits

    @property
    def stop(self):
        return self._params.stop

    @stop.setter
    def stop(self, value: int):
        if value not in [1, 2]:
            raise ValueError
        self._params.stop = value
        self.update_eof()
        self.on_change()

    @property
    def eof_ms(self):
        return self._params.eof_ms

    @eof_ms.setter
    def eof_ms(self, value: int):
        if not 0 < value < 1000:
            raise ValueError
        self._params.eof_ms = value
        self.on_change()

    def update_eof(self):
        # automatic update of end of frame (eof) delay
        # it's a silence on rx line > 3.5 * byte transmit time
        byte_len = 10 + self._params.stop
        if self._params.parity is not None:
            byte_len += 1
        byte_tx_ms = 1000 * byte_len / self._params.baudrate
        self.eof_ms = max(round(3.5 * byte_tx_ms), 1)

    def on_change(self):
        pass

    def __str__(self) -> str:
        return f'{self.baudrate},{self.parity_as_str},{self.bits},{self.stop}'


class UserCli(Cmd):
    intro = 'modbus spy tool (type help)'

    def __init__(self, **kwargs):
        super().__init__(self, **kwargs)
        self.serial_cnf = SerialConf()
        self.serial_cnf.on_change = self.on_serial_change

    def on_serial_change(self):
        print("call on_serial_change()")
        # load new serial conf
        with spy_job.conf.lock:
            spy_job.conf.serial = self.serial_cnf.params
        # notify spy job to reload serial conf
        spy_job.reload_flag.set()

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
                self.stdout.write(f'unable to set baudrate (allowed values between 300 and 115200 bauds)\n')
        else:
            self.stdout.write(f'current value of baudrate is {self.serial_cnf.baudrate} bauds\n')

    def help_baudrate(self):
        self.stdout.write('set the baudrate of the spied line (example: "baudrate 115200")\n')

    def do_parity(self, arg: str):
        if arg:
            try:
                self.serial_cnf.parity_as_str = arg.strip().upper()
            except ValueError:
                self.stdout.write(f'unable to set parity\n')
        else:
            self.stdout.write(f'current value of parity is {self.serial_cnf.parity_as_str}\n')

    def help_parity(self):
        self.stdout.write('set the parity to N, E or O (example: "parity E")\n')

    def do_stop(self, arg: str):
        if arg:
            try:
                self.serial_cnf.stop = int(arg.strip())
            except ValueError:
                self.stdout.write(f'unable to set the number of stop bit(s) (allowed values: 1 or 2)\n')
        else:
            self.stdout.write(f'current number of stop bit(s) is {self.serial_cnf.stop}\n')

    def help_stop(self):
        self.stdout.write('set the number of stop bit(s) (example: "stop 1")\n')

    def do_eof(self, arg: str):
        if arg:
            try:
                self.serial_cnf.eof_ms = int(arg.strip().upper())
            except ValueError:
                self.stdout.write(f'unable to set eof (valid between 1 and 999 ms)\n')
        else:
            self.stdout.write(f'current value of end of frame delay is {self.serial_cnf.eof_ms} ms\n')

    def help_eof(self):
        self.stdout.write('set the end of frame silent delay in ms (example: "eof 3")\n')

    def do_dump(self, arg: str):
        # parse arg if available
        if arg:
            try:
                frame_nb = int(arg.strip())
            except ValueError:
                self.stdout.write(f'unable to parse frame number\n')
                return
        else:
            frame_nb = 10
        # copy requested values from spy job
        with spy_job.data.lock:
            dump_l = spy_job.data.frames_l[-frame_nb:].copy()
        # dump it
        for idx, frame in enumerate(dump_l):
            # format dump message
            crc_str = ('ERR', 'OK')[frame.crc_is_valid]
            # print dump message
            print(f'[{idx:>3d}/{len(frame):>3}/{crc_str:<3}] {frame}')

    def help_dump(self):
        self.stdout.write('show an hex dump of n last receive frames (example: "dump 10" to dump last 10 frames)\n')

    def do_version(self, _arg):
        self.stdout.write(f'modbus spy tool {VERSION}\n')

    def help_version(self):
        self.stdout.write('show the current version\n')

    def help_help(self):
        self.stdout.write('show help message about available commands\n')


class SpyJob:
    class Data:
        def __init__(self) -> None:
            self.lock = _thread.allocate_lock()
            self.frames_l = []

    class Conf:
        def __init__(self) -> None:
            self.lock = _thread.allocate_lock()
            self.serial = SerialConf.Params()

    def __init__(self) -> None:
        # flags
        self.exit_flag = ThreadFlag()
        self.reload_flag = ThreadFlag()
        # data
        self.data = self.Data()
        # conf
        self.conf = self.Conf()

    def run(self):
        # task loop
        while True:
            # reset reload flag
            self.reload_flag.unset()
            # load UART conf
            with self.conf.lock:
                uart = UART(UART_ID, tx=UART_TX, rx=UART_RX,
                            baudrate=self.conf.serial.baudrate,
                            bits=self.conf.serial.bits,
                            parity=self.conf.serial.parity,
                            stop=self.conf.serial.stop,
                            timeout_char=self.conf.serial.eof_ms,
                            rxbuf=256, timeout=0)
            # frame recv loop
            while True:
                # try to read at max 256 bytes, return when timeout_char expire
                recv_frame = uart.read(256)
                # when frame is set
                if recv_frame:
                    with self.data.lock:
                        if len(self.data.frames_l) >= FRAMES_BUF_SIZE:
                            self.data.frames_l.pop(0)
                        self.data.frames_l.append(ModbusFrame(recv_frame))
                # exit recv loop on job exit or reload request
                if self.exit_flag.is_set() or self.reload_flag.is_set():
                    break
            # deinit UART
            uart.deinit()
            # exit on request (avoid OSError: core1 in use )
            if self.exit_flag.is_set():
                break


class CliJob:
    def __init__(self, spy_job: SpyJob) -> None:
        self.spy_job = spy_job

    def run(self):
        try:
            UserCli().cmdloop()
        except KeyboardInterrupt:
            self.spy_job.exit_flag.set()


if __name__ == '__main__':
    # init
    spy_job = SpyJob()
    cli_job = CliJob(spy_job)
    # launch spy job on core1
    _thread.start_new_thread(spy_job.run, ())
    # launch cli job on core0
    cli_job.run()
