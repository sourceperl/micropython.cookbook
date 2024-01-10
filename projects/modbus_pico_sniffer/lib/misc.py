import _thread


class SerialConf:
    class Params:
        def __init__(self) -> None:
            self.baudrate: int = 9600
            self.parity: int = None
            self.bits: int = 8
            self.stop = 1
            self.eof_ms: float = 4.0

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
            raise ValueError('unable to set baudrate (allowed values between 300 and 115200 bauds)')
        self._params.baudrate = value
        self._on_write()

    @property
    def parity_as_str(self):
        return {None: 'N', 0: 'E', 1: 'O'}[self._params.parity]

    @parity_as_str.setter
    def parity_as_str(self, value: str):
        try:
            value = value.upper()
            parity_char = {'N': None, 'E': 0, 'O': 1}[value]
            self._params.parity = parity_char
            self._on_write()
        except (KeyError, AttributeError):
            raise ValueError("unable to set parity (allowed values are 'N', 'E' or 'O')")

    @property
    def parity_as_int(self):
        return self._params.parity

    @parity_as_int.setter
    def parity_as_int(self, value: int):
        if value not in [None, 0, 1]:
            raise ValueError('unable to set parity (allowed values are None, 0 or 1)')
        self._params.parity = value
        self._on_write()

    @property
    def bits(self):
        return self._params.bits

    @property
    def stop(self):
        return self._params.stop

    @stop.setter
    def stop(self, value: int):
        if value not in [1, 2]:
            raise ValueError('unable to set the number of stop bit(s) (allowed values: 1 or 2)')
        self._params.stop = value
        self._on_write()

    @property
    def eof_ms(self):
        return self._params.eof_ms

    @eof_ms.setter
    def eof_ms(self, value: float):
        if not 0.0 < value < 1000.0:
            raise ValueError
        self._params.eof_ms = round(value, 3)
        self._on_write(skip_eof=True)

    def _on_write(self, skip_eof=False):
        if not skip_eof:
            self._update_eof()
        self.on_change()

    def _update_eof(self):
        # auto update end of frame delay (eof) on property write
        # eof = silence on rx line > 3.5 * byte transmit time
        byte_len = 9 + self._params.stop
        if self._params.parity is not None:
            byte_len += 1
        bit_rate_ms = 1000 / self._params.baudrate
        byte_tx_ms = bit_rate_ms * byte_len
        compute_eof_ms = 3.5 * byte_tx_ms
        self.eof_ms = max(compute_eof_ms, 0.4)

    def on_change(self):
        pass

    def __str__(self) -> str:
        return f'{self.baudrate},{self.parity_as_str},{self.bits},{self.stop} [eof={self.eof_ms} ms]'


class ThreadFlag:
    """ A thread safe flag class """

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
