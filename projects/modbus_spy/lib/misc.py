import _thread


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
