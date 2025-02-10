"""
RS-485 modbus RTU sniffer tool.

Test on board SparkFun Pro Micro RP2040.

Issues with MicroPython versions greater than v1.21.0.
Further testing with MicroPython 1.25.0-preview.273.gb2ce9b6fb (2025-02-08) indicates that the functionality
has been restored.
This improvement is likely due to the fix for 'rp2/rp2_flash: multicore lock workaround not reset.'
"""

import _thread
import json
import sys
from time import sleep_ms, ticks_diff, ticks_us

import micropython
from lib.misc import SerialConf, ThreadFlag
from lib.modbus import FrameAnalyzer, frame_is_ok
from machine import UART, Pin
from micropython import const

from neopixel import NeoPixel

# some const
_BUF_SIZE = const(25)
_UART_ID = const(0)
_UART_TX_PIN = const(16)
_UART_RX_PIN = const(17)
_WS2812_PIN = const(25)


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
            # frame index: point to the head of frame list (next insert point))
            self.frm_idx = 0
            # frame list: ensure mem allocs for _BUF_SIZE
            self.frm_l = [bytearray()] * _BUF_SIZE

        def clear(self):
            self.lock.acquire()
            self.frm_idx = 0
            self.lock.release()

        @micropython.native
        def exp_frm(self, clear=False):
            # secure export of frames list (clean frm_l buffer after if ad-hoc arg set to True)
            self.lock.acquire()
            # copy internal to cache (free lock as fast as possible)
            _frm_idx = self.frm_idx
            _frm_l = self.frm_l.copy()
            # reset frame index after export if requested
            if clear:
                self.frm_idx = 0
            self.lock.release()
            # head_idx: current insert point
            # frm_l [ [f#3], [f#4], [f#5: head_idx] [f#1], [f#2] ]
            head_idx = _frm_idx % _BUF_SIZE
            # export list with last frames
            if _frm_idx < _BUF_SIZE:
                return _frm_l[:head_idx]
            else:
                return _frm_l[head_idx:] + _frm_l[:head_idx]

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
        self._rcv_flag = ThreadFlag()
        # I/O LED
        self.io_led = NeoPixel(Pin(_WS2812_PIN), 1)

    @property
    def is_on(self):
        return self._rcv_flag.is_set()

    def on(self):
        self._rcv_flag.set()

    def off(self):
        self._rcv_flag.unset()

    @micropython.native
    def run(self):
        # task loop
        while True:
            # wait sniffer is turn on
            while not self._rcv_flag.is_set():
                sleep_ms(100)
            # load UART conf
            self.conf.lock.acquire()
            uart = UART(_UART_ID,
                        tx=Pin(_UART_TX_PIN, Pin.IN),
                        rx=Pin(_UART_RX_PIN, Pin.IN),
                        baudrate=self.conf.serial.baudrate,
                        bits=self.conf.serial.bits,
                        parity=self.conf.serial.parity_as_int,
                        stop=self.conf.serial.stop,
                        # timeout=-1,
                        # timeout_char=-1,
                        rxbuf=256)
            eof_us = round(self.conf.serial.eof_ms * 1000)
            self.conf.lock.release()
            # reset frames index
            self.data.lock.acquire()
            self.data.frm_idx = 0
            self.data.lock.release()
            # init recv loop vars
            read_nb = 0
            rcv_us = 0
            # skip first frame
            uart.read()
            # recv loop (keep this as fast as possible)
            while self._rcv_flag.is_set():
                # mark time of arrival
                u_any = uart.any()
                if u_any > read_nb:
                    rcv_us = ticks_us()
                read_nb = u_any
                # if data available and silence greater than EOF us -> read it
                if read_nb and ticks_diff(ticks_us(), rcv_us) > eof_us:
                    read_bytes = uart.read(read_nb)
                    read_nb = 0
                    self.data.lock.acquire()
                    self.data.frm_l[self.data.frm_idx % _BUF_SIZE] = read_bytes
                    self.data.frm_idx += 1
                    self.data.lock.release()
            # deinit UART
            uart.deinit()


class App:
    VERSION = '0.0.1'
    JS_CONF_FILE = 'config.json'

    class AppSerial:
        def __init__(self, app: "App") -> None:
            self._app = app

        @property
        def baudrate(self):
            with self._app.sniff_job.conf as conf:
                return conf.serial.baudrate

        @baudrate.setter
        def baudrate(self, value: int):
            try:
                with self._app.sniff_job.conf as conf:
                    conf.serial.baudrate = value
                self._app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def parity(self):
            with self._app.sniff_job.conf as conf:
                return conf.serial.parity_as_str

        @parity.setter
        def parity(self, value: str):
            try:
                with self._app.sniff_job.conf as conf:
                    conf.serial.parity_as_str = value
                self._app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def eof_ms(self):
            with self._app.sniff_job.conf as conf:
                return conf.serial.eof_ms

        @eof_ms.setter
        def eof_ms(self, value: float):
            try:
                with self._app.sniff_job.conf as conf:
                    conf.serial.eof_ms = round(value, 3)
                self._app._update_ps()
            except ValueError as e:
                print(e)

        @property
        def stop(self):
            with self._app.sniff_job.conf as conf:
                return conf.serial.stop

        @stop.setter
        def stop(self, value: int):
            try:
                with self._app.sniff_job.conf as conf:
                    conf.serial.stop = value
                self._app._update_ps()
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
            print(f'{self.JS_CONF_FILE} file have bad format\n')
        except OSError:
            pass

    def _update_ps(self):
        with self.sniff_job.conf as conf:
            serial_str = str(conf.serial)
        sys.ps1 = f'{serial_str}> '

    def analyze(self):
        # check sniffer is on
        if not self.sniff_job.is_on:
            self.sniff_job.on()
        # start real time dump
        try:
            # frame index
            msg_idx = 0
            # avoid polluting real time list with historic value
            self.sniff_job.data.clear()
            while True:
                # copy requested values from sniff job
                frm_l = self.sniff_job.data.exp_frm(clear=True)
                # analyze frames
                fa_session = FrameAnalyzer()
                for frame in frm_l:
                    # format dump message
                    dec_str = fa_session.analyze(frame)
                    ok_str = 'OK' if fa_session.frm_now.is_valid else 'ERR'
                    # print dump message
                    print(f'[{msg_idx:>3d}/{len(frame):>3}/{ok_str:<3}] {dec_str}')
                    # update frame index
                    msg_idx += 1
                # avoid overload
                sleep_ms(100)
        except KeyboardInterrupt:
            pass

    def dump(self):
        # check sniffer is on
        if not self.sniff_job.is_on:
            self.sniff_job.on()
        # start real time dump
        try:
            # frame index
            msg_idx = 0
            # avoid polluting real time list with historic value
            self.sniff_job.data.clear()
            # msg loop
            while True:
                # copy requested values from sniff job
                frm_l = self.sniff_job.data.exp_frm(clear=True)
                # dump it
                for frame in frm_l:
                    # format dump message
                    f_str = '-'.join(['%02X' % x for x in frame])
                    is_ok = frame_is_ok(frame)
                    ok_str = 'OK' if is_ok else 'ERR'
                    # print dump message
                    print(f'[{msg_idx:>3d}/{len(frame):>3}/{ok_str:<3}] {f_str}')
                    # update frame index
                    msg_idx += 1
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

    def version(self):
        print(f'modbus sniffer tool {self.VERSION}')


# create app instance
sniff_job = SniffJob()
app = App(sniff_job=sniff_job)

# shortcuts to expose on micropython REPL
analyze = app.analyze
dump = app.dump
save = app.save
serial = app.serial
version = app.version
