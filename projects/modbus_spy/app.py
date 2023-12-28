import _thread
import json
import machine
import sys
from lib.misc import ThreadFlag, SerialConf
from lib.modbus import FrameAnalyzer, frame_is_ok


# some class
class SpyJob:
    FRAMES_BUF_SIZE = 100
    UART_ID = 1
    UART_TX = machine.Pin(4, machine.Pin.IN)
    UART_RX = machine.Pin(5, machine.Pin.IN)

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
        self.spy_on_flag = ThreadFlag()
        self.reload_flag = ThreadFlag()
        # conf
        self.conf = self.Conf()
        self.conf.serial.on_change = lambda: self.reload_flag.set()
        # data
        self.data = self.Data()

    def run(self):
        # task loop
        while True:
            # reset reload flag
            self.reload_flag.unset()
            # load UART conf
            with self.conf as conf:
                uart = machine.UART(self.UART_ID, tx=self.UART_TX, rx=self.UART_RX,
                                    baudrate=conf.serial.baudrate,
                                    bits=conf.serial.bits,
                                    parity=conf.serial.parity_as_int,
                                    stop=conf.serial.stop,
                                    timeout_char=conf.serial.eof_ms,
                                    rxbuf=256, timeout=0)
            # skip first frame
            uart.read(256)
            # frame recv loop
            while True:
                # if spy mode is turn on
                if self.spy_on_flag.is_set():
                    # try to read at max 256 bytes, return when timeout_char expire
                    recv_frame = uart.read(256)
                    # when frame is set
                    if recv_frame:
                        with self.data as data:
                            if len(data.frames_l) >= self.FRAMES_BUF_SIZE:
                                data.frames_l.pop(0)
                            data.frames_l.append(recv_frame)
                # exit recv loop on job exit or reload request
                if self.reload_flag.is_set():
                    break
            # deinit UART
            uart.deinit()


class App:

    VERSION = '0.0.1'
    JS_CONF_FILE = 'config.json'

    class AppSerial:
        def __init__(self, app: "App") -> None:
            self.app = app

        @property
        def baudrate(self):
            with self.app.spy_job.conf as conf:
                return conf.serial.baudrate

        @baudrate.setter
        def baudrate(self, value: int):
            try:
                with self.app.spy_job.conf as conf:
                    conf.serial.baudrate = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def parity(self):
            with self.app.spy_job.conf as conf:
                return conf.serial.parity_as_str

        @parity.setter
        def parity(self, value: str):
            try:
                with self.app.spy_job.conf as conf:
                    conf.serial.parity_as_str = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def eof_ms(self):
            with self.app.spy_job.conf as conf:
                return conf.serial.eof_ms

        @eof_ms.setter
        def eof_ms(self, value: int):
            try:
                with self.app.spy_job.conf as conf:
                    conf.serial.eof_ms = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def stop(self):
            with self.app.spy_job.conf as conf:
                return conf.serial.stop

        @stop.setter
        def stop(self, value: int):
            try:
                with self.app.spy_job.conf as conf:
                    conf.serial.stop = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

    def __init__(self, spy_job: SpyJob) -> None:
        # init spy job
        self.spy_job = spy_job
        # a link to serial params
        self.serial = self.AppSerial(self)
        # launch the spy job on second core
        _thread.start_new_thread(self.spy_job.run, ())
        # load initial values
        self._startup_load()
        # turn on spy at startup
        self.spy_job.spy_on_flag.set()
        # init
        self._update_ps()

    def _startup_load(self):
        # load serial conf from file (if it exists)
        try:
            # load and decode json
            conf_d = json.load(open(self.JS_CONF_FILE))
            serial_d = conf_d['serial']
            # apply it to spy job
            with self.spy_job.conf as conf:
                conf.serial.baudrate = serial_d.get('baudrate', conf.serial.baudrate)
                conf.serial.parity_as_str = serial_d.get('parity', conf.serial.parity_as_str)
                conf.serial.stop = serial_d.get('stop', conf.serial.stop)
                conf.serial.eof_ms = serial_d.get('eof_ms', conf.serial.eof_ms)
            # reload spy job
            self.spy_job.reload_flag.set()
        except (KeyError, ValueError):
            self.stdout.write(f'{self.JS_CONF_FILE} file have bad format\n')
        except OSError:
            pass

    def _update_ps(self):
        status_str = 'on' if self.spy_job.spy_on_flag.is_set() else 'off'
        with self.spy_job.conf as conf:
            serial_str = str(conf.serial)
        sys.ps1 = f'{serial_str}:{status_str}> '

    @property
    def version(self):
        return f'modbus spy tool {self.VERSION}\n'

    def on(self):
        self.spy_job.spy_on_flag.set()
        self._update_ps()

    def off(self):
        self.spy_job.spy_on_flag.unset()
        self._update_ps()

    def clear(self):
        with self.spy_job.data as data:
            data.frames_l.clear()
        self._update_ps()

    def dump(self, n: int = 10):
        try:
            # copy requested values from spy job
            with self.spy_job.data as data:
                dump_l = data.frames_l[-n:].copy()
            # dump it
            for idx, frame in enumerate(dump_l):
                # format dump message
                f_str = '-'.join(['%02X' % x for x in frame])
                ok_str = ('ERR', 'OK')[frame_is_ok(frame)]
                # print dump message
                print(f'[{idx:>3d}/{len(frame):>3}/{ok_str:<3}] {f_str}')
        except KeyboardInterrupt:
            pass

    def _dump_rt(self):
        try:
            # frame index
            idx = 0
            while True:
                # copy requested values from spy job
                with self.spy_job.data as data:
                    dump_l = data.frames_l.copy()
                    data.frames_l.clear()
                # dump it
                for frame in dump_l:
                    # format dump message
                    f_str = '-'.join(['%02X' % x for x in frame])
                    ok_str = ('ERR', 'OK')[frame_is_ok(frame)]
                    # print dump message
                    print(f'[{idx:>3d}/{len(frame):>3}/{ok_str:<3}] {f_str}')
                    # update frame index
                    idx += 1
        except KeyboardInterrupt:
            pass

    def analyze(self, n: int = 10):
        try:
            # copy requested values from spy job
            with self.spy_job.data as data:
                dump_l = data.frames_l[-n:].copy()
            # analyze frames
            fa_session = FrameAnalyzer()
            for idx, frame in enumerate(dump_l):
                # format dump message
                dec_str = fa_session.analyze(frame)
                ok_str = ('ERR', 'OK')[fa_session.frm_now.is_valid]
                # print dump message
                print(f'[{idx:>3d}/{len(frame):>3}/{ok_str:<3}] {dec_str}')
        except KeyboardInterrupt:
            pass

    def _analyze_rt(self):
        try:
            # frame index
            idx = 0
            while True:
                # copy requested values from spy job
                with self.spy_job.data as data:
                    dump_l = data.frames_l.copy()
                    data.frames_l.clear()
                # analyze frames
                fa_session = FrameAnalyzer()
                for frame in dump_l:
                    # format dump message
                    dec_str = fa_session.analyze(frame)
                    ok_str = ('ERR', 'OK')[fa_session.frm_now.is_valid]
                    # print dump message
                    print(f'[{idx:>3d}/{len(frame):>3}/{ok_str:<3}] {dec_str}')
                    # update frame index
                    idx += 1
        except KeyboardInterrupt:
            pass

    def save(self):
        # extract current configuration
        with self.spy_job.conf as conf:
            serial_d = dict(baudrate=conf.serial.baudrate,
                            parity=conf.serial.parity_as_str,
                            stop=conf.serial.stop,
                            eof_ms=conf.serial.eof_ms)
        conf_d = dict(serial=serial_d)
        # save it as json file
        with open(self.JS_CONF_FILE, 'w') as f:
            f.write(json.dumps(conf_d))


# overclock from default 125 MHz to 250 MHz
# not essential, but improve responsiveness on the USB interface
machine.freq(250_000_000)

# create app instance
spy_job = SpyJob()
app = App(spy_job=spy_job)

# shortcuts to expose on micropyhon REPL
serial = app.serial
dump = app.dump
analyze = app.analyze
on = app.on
off = app.off
clear = app.clear
save = app.save

# experimental
_dump_rt = app._dump_rt
_analyze_rt = app._analyze_rt
