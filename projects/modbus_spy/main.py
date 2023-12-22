import _thread
from machine import Pin, UART
from lib.cmd import Cmd
from lib.misc import SerialConf, ThreadFlag
from lib.modbus import ModbusFrame


# some const
VERSION = '0.0.1'
FRAMES_BUF_SIZE = 100
UART_ID = 1
UART_TX = Pin(4, Pin.IN)
UART_RX = Pin(5, Pin.IN)


# some class
class SpyJob:
    class Conf:
        def __init__(self) -> None:
            self.lock = _thread.allocate_lock()
            self.serial = SerialConf()

        def __enter__(self):
            self.lock.acquire()
            return self

        def __exit__(self, _exc_type, _exc_val, _exc_tb):
            self.lock.release()

    class Data:
        def __init__(self) -> None:
            self.lock = _thread.allocate_lock()
            self.frames_l = []

        def __enter__(self):
            self.lock.acquire()
            return self

        def __exit__(self, _exc_type, _exc_val, _exc_tb):
            self.lock.release()

    def __init__(self) -> None:
        # flags
        self.exit_flag = ThreadFlag()
        self.reload_flag = ThreadFlag()
        # conf
        self.conf = self.Conf()
        self.conf.serial.on_change = lambda: self.reload_flag.set()
        # data
        self.spy_data = self.Data()

    def run(self):
        # task loop
        while True:
            # reset reload flag
            self.reload_flag.unset()
            # load UART conf
            with self.conf as conf:
                uart = UART(UART_ID, tx=UART_TX, rx=UART_RX,
                            baudrate=conf.serial.baudrate,
                            bits=conf.serial.bits,
                            parity=conf.serial.parity_as_int,
                            stop=conf.serial.stop,
                            timeout_char=conf.serial.eof_ms,
                            rxbuf=256, timeout=0)
            # frame recv loop
            while True:
                # try to read at max 256 bytes, return when timeout_char expire
                recv_frame = uart.read(256)
                # when frame is set
                if recv_frame:
                    with self.spy_data.lock:
                        if len(self.spy_data.frames_l) >= FRAMES_BUF_SIZE:
                            self.spy_data.frames_l.pop(0)
                        self.spy_data.frames_l.append(ModbusFrame(recv_frame))
                # exit recv loop on job exit or reload request
                if self.exit_flag.is_set() or self.reload_flag.is_set():
                    break
            # deinit UART
            uart.deinit()
            # exit on request (avoid OSError: core1 in use )
            if self.exit_flag.is_set():
                break


class CliJob:
    class UserCli(Cmd):
        intro = 'modbus spy tool (type help)'

        def __init__(self, spy_job: SpyJob, **kwargs):
            # keep a ref to spy job
            self.spy_job = spy_job
            # origin Cmd constructor
            super().__init__(self, **kwargs)

        @property
        def prompt(self):
            with self.spy_job.conf.lock:
                return f'{self.spy_job.conf.serial}> '

        def emptyline(self):
            # on empty line do nothing (default behaviour repeat last cmd)
            return False

        def do_baudrate(self, arg: str):
            with self.spy_job.conf as conf:
                if arg:
                    try:
                        conf.serial.baudrate = int(arg)
                        self.stdout.write(f'baudrate set to {conf.serial.baudrate} bauds\n')
                    except ValueError:
                        self.stdout.write(f'unable to set baudrate (allowed values between 300 and 115200 bauds)\n')
                else:
                    self.stdout.write(f'current value of baudrate is {conf.serial.baudrate} bauds\n')

        def help_baudrate(self):
            self.stdout.write('set the baudrate of the spied line (example: "baudrate 115200")\n')

        def do_parity(self, arg: str):
            with self.spy_job.conf as conf:
                if arg:
                    try:
                        conf.serial.parity_as_str = arg.strip().upper()
                        self.stdout.write(f'parity set to {conf.serial.parity_as_str}\n')
                    except ValueError:
                        self.stdout.write(f'unable to set parity\n')
                else:
                    self.stdout.write(f'current value of parity is {conf.serial.parity_as_str}\n')

        def help_parity(self):
            self.stdout.write('set the parity to N, E or O (example: "parity E")\n')

        def do_stop(self, arg: str):
            with self.spy_job.conf as conf:
                if arg:
                    try:
                        conf.serial.stop = int(arg.strip())
                        self.stdout.write(f'stop bit(s) set to {conf.serial.stop}\n')
                    except ValueError:
                        self.stdout.write(f'unable to set the number of stop bit(s) (allowed values: 1 or 2)\n')
                else:
                    self.stdout.write(f'current number of stop bit(s) is {conf.serial.stop}\n')

        def help_stop(self):
            self.stdout.write('set the number of stop bit(s) (example: "stop 1")\n')

        def do_eof(self, arg: str):
            with self.spy_job.conf as conf:
                if arg:
                    try:
                        conf.serial.eof_ms = int(arg.strip().upper())
                        self.stdout.write(f'eof set to {conf.serial.eof_ms} ms\n')
                    except ValueError:
                        self.stdout.write(f'unable to set eof (valid between 1 and 999 ms)\n')
                else:
                    self.stdout.write(f'current value of end of frame delay is {conf.serial.eof_ms} ms\n')

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
            with self.spy_job.spy_data as data:
                dump_l = data.frames_l[-frame_nb:].copy()
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

    def __init__(self, spy_job: SpyJob) -> None:
        self.spy_job = spy_job
        self.user_cli = self.UserCli(spy_job)

    def run(self):
        try:
            self.user_cli.cmdloop()
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
