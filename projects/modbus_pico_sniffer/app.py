"""
RS-485 modbus RTU sniffer tool.

Test on Raspberry Pico (overclock to 250 MHz) with micropython v1.21.0.
"""

import _thread
import json
import machine
from micropython import const
from time import ticks_diff, ticks_us, sleep_ms
import sys
from lib.misc import ThreadFlag, SerialConf
from lib.modbus import FrameAnalyzer, frame_is_ok


# some const
_BUF_SIZE = const(100)
_UART_ID = const(1)
_UART_TX_PIN = const(4)
_UART_RX_PIN = const(5)


# some class
class SniffJob:

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
        # conf
        self.conf = self.Conf()
        self.conf.serial.on_change = self.off
        # data
        self.data = self.Data()
        # flags
        self._recv_flag = ThreadFlag()

    @property
    def is_on(self):
        return self._recv_flag.is_set()

    def on(self):
        self._recv_flag.set()

    def off(self):
        self._recv_flag.unset()

    def run(self):
        # task loop
        while True:
            # wait sniffer is turn on
            while not self._recv_flag.is_set():
                sleep_ms(100)
            # load UART conf
            with self.conf as conf:
                uart = machine.UART(_UART_ID,
                                    tx=machine.Pin(_UART_TX_PIN, machine.Pin.IN),
                                    rx=machine.Pin(_UART_RX_PIN, machine.Pin.IN),
                                    baudrate=conf.serial.baudrate,
                                    bits=conf.serial.bits,
                                    parity=conf.serial.parity_as_int,
                                    stop=conf.serial.stop,
                                    timeout=-1,
                                    timeout_char=-1,
                                    rxbuf=256)
                eof_us = round(conf.serial.eof_ms * 1000)
            # clear frames list
            with self.data as data:
                data.frames_l.clear()
            # init recv loop vars
            buf = bytearray(256)
            buf_s, _buf_s = 0, 0
            rcv_t = 0
            read_n = 0
            # skip first frame
            uart.read()
            # recv loop (keep this as fast as possible)
            while self._recv_flag.is_set():
                # mark time of arrival
                buf_s = uart.any()
                if buf_s > _buf_s:
                    rcv_t = ticks_us()
                _buf_s = buf_s
                # if data available and silence greater than EOF us -> read it
                if buf_s and ticks_diff(ticks_us(), rcv_t) > eof_us:
                    read_n = uart.readinto(buf, buf_s)
                # on next cycle, try to add the last receive frame to frames list
                # try an immediate lock acquire or skip and try later
                elif read_n and self.data.lock.acquire(False):
                    if len(self.data.frames_l) >= _BUF_SIZE:
                        self.data.frames_l.pop(0)
                    self.data.frames_l.append(buf[:read_n])
                    self.data.lock.release()
                    read_n = 0
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
            with self.app.sniff_job.conf as conf:
                return conf.serial.baudrate

        @baudrate.setter
        def baudrate(self, value: int):
            try:
                with self.app.sniff_job.conf as conf:
                    conf.serial.baudrate = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def parity(self):
            with self.app.sniff_job.conf as conf:
                return conf.serial.parity_as_str

        @parity.setter
        def parity(self, value: str):
            try:
                with self.app.sniff_job.conf as conf:
                    conf.serial.parity_as_str = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def eof_ms(self):
            with self.app.sniff_job.conf as conf:
                return conf.serial.eof_ms

        @eof_ms.setter
        def eof_ms(self, value: float):
            try:
                with self.app.sniff_job.conf as conf:
                    conf.serial.eof_ms = round(value, 3)
                self.app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def stop(self):
            with self.app.sniff_job.conf as conf:
                return conf.serial.stop

        @stop.setter
        def stop(self, value: int):
            try:
                with self.app.sniff_job.conf as conf:
                    conf.serial.stop = value
                self.app._update_ps()
            except ValueError as e:
                print(e)

    def __init__(self, sniff_job: SniffJob) -> None:
        # init sniff job
        self.sniff_job = sniff_job
        # a link to serial params
        self.serial = self.AppSerial(self)
        # launch the sniff job on second core
        _thread.start_new_thread(self.sniff_job.run, ())
        # load initial values
        self._startup_load()
        # turn on sniff at startup
        self.sniff_job.on()
        # init
        self._update_ps()

    def _startup_load(self):
        # load serial conf from file (if it exists)
        try:
            # load and decode json
            conf_d = json.load(open(self.JS_CONF_FILE))
            serial_d = conf_d['serial']
            # apply it to sniff job
            with self.sniff_job.conf as conf:
                conf.serial.baudrate = serial_d.get('baudrate', conf.serial.baudrate)
                conf.serial.parity_as_str = serial_d.get('parity', conf.serial.parity_as_str)
                conf.serial.stop = serial_d.get('stop', conf.serial.stop)
                conf.serial.eof_ms = serial_d.get('eof_ms', conf.serial.eof_ms)
        except (KeyError, ValueError):
            self.stdout.write(f'{self.JS_CONF_FILE} file have bad format\n')
        except OSError:
            pass

    def _update_ps(self):
        status_str = 'on' if self.sniff_job.is_on else 'off'
        with self.sniff_job.conf as conf:
            serial_str = str(conf.serial)
        sys.ps1 = f'{serial_str}:{status_str}> '

    @property
    def version(self):
        return f'modbus sniffer tool {self.VERSION}\n'

    def on(self):
        self.sniff_job.on()
        self._update_ps()

    def off(self):
        self.sniff_job.off()
        self._update_ps()

    def clear(self):
        with self.sniff_job.data as data:
            data.frames_l.clear()
        self._update_ps()

    def dump(self, n: int = 10):
        try:
            # copy requested values from sniff job
            with self.sniff_job.data as data:
                dump_l = data.frames_l[-n:]
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
                # copy requested values from sniff job
                with self.sniff_job.data as data:
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
                # avoid overload
                sleep_ms(100)
        except KeyboardInterrupt:
            pass

    def analyze(self, n: int = 10):
        try:
            # copy requested values from sniff job
            with self.sniff_job.data as data:
                dump_l = data.frames_l[-n:]
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
                # copy requested values from sniff job
                with self.sniff_job.data as data:
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
                # avoid overload
                sleep_ms(100)
        except KeyboardInterrupt:
            pass

    def save(self):
        # extract current configuration
        with self.sniff_job.conf as conf:
            serial_d = dict(baudrate=conf.serial.baudrate,
                            parity=conf.serial.parity_as_str,
                            stop=conf.serial.stop,
                            eof_ms=conf.serial.eof_ms)
        conf_d = dict(serial=serial_d)
        # save it as json file
        with open(self.JS_CONF_FILE, 'w') as f:
            f.write(json.dumps(conf_d))


# overclock Pico from default 125 MHz to 250 MHz
# not essential, but improve responsiveness on the USB interface
machine.freq(250_000_000)

# create app instance
sniff_job = SniffJob()
app = App(sniff_job=sniff_job)

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
