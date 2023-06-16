""" A BLE UART peripheral, command a pico W built-in LED with on, off or toggle commands. """

from time import sleep_ms
import bluetooth
from lib.ble_advertising import advertising_payload
from machine import Pin
from micropython import const

# some const
EVT_CENTRAL_CONNECT = const(1)
EVT_CENTRAL_DISCONNECT = const(2)
EVT_GATTS_WRITE = const(3)
FLAG_WRITE = const(0x0008)
FLAG_NOTIFY = const(0x0010)
# Nordic UART Service
UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
UART_UUID_RX = (bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E'), FLAG_WRITE,)
UART_UUID_TX = (bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E'), FLAG_NOTIFY,)
UART_SERVICE = (UART_UUID, (UART_UUID_TX, UART_UUID_RX),)


class BLE_UART:
    def __init__(self, ble: bluetooth.BLE, name: str = '', rx_buf_size: int = 100):
        # public args
        self.ble = ble
        self.name = name
        self.rx_buf_size = rx_buf_size
        # init internal structs
        self._connections = set()
        self._rx_buffer = bytearray()
        # turn on ble
        self.ble.active(True)
        self.ble.irq(self._evt_handler)
        ((self._tx_handle, self._rx_handle),) = self.ble.gatts_register_services((UART_SERVICE,))
        # set _rx_handle size in bytes and turn on append mode
        self.ble.gatts_set_buffer(self._rx_handle, self.rx_buf_size, True)
        # start BLE advertising
        self._advertise()

    def _advertise(self, every_us=500_000):
        # start BLE advertising (default rate is every 500 ms)
        self.ble.gap_advertise(every_us, advertising_payload(name=self.name, services=[UART_UUID]))

    def _evt_handler(self, event, data):
        # track connections so we can send notifications
        if event == EVT_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == EVT_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            # start advertising again to allow new connection
            self._advertise()
        elif event == EVT_GATTS_WRITE:
            conn_handle, value_handle = data
            if conn_handle in self._connections and value_handle == self._rx_handle:
                self._rx_buffer += self.ble.gatts_read(self._rx_handle)
                self.on_write()

    def any(self):
        return len(self._rx_buffer)

    def read(self, sz=None):
        if not sz:
            sz = len(self._rx_buffer)
        result = self._rx_buffer[0:sz]
        self._rx_buffer = self._rx_buffer[sz:]
        return result

    def write(self, data):
        for conn_handle in self._connections:
            self.ble.gatts_notify(conn_handle, self._tx_handle, data)

    def on_write(self):
        pass

    def close(self):
        for conn_handle in self._connections:
            self.ble.gap_disconnect(conn_handle)
        self._connections.clear()


if __name__ == "__main__":
    # I/O init
    led = Pin('LED', Pin.OUT)
    # bluetooth init
    ble = bluetooth.BLE()
    uart = BLE_UART(ble, name='LED_UART')
    # uart.on_write = lambda: print('rx: ', uart.read().decode().strip())

    # main loop (exit with ctrl-c)
    try:
        while True:
            if uart.any():
                cmd = uart.read().decode().strip().lower()
                if cmd == 'on':
                    led.on()
                    uart.write('Turn on built-in LED\n')
                elif cmd == 'off':
                    led.off()
                    uart.write('Turn off built-in LED\n')
                elif cmd == 'toggle':
                    led.toggle()
                    uart.write('Toggle built-in LED\n')
                else:
                    uart.write('Unknown command (valid are "on", "off", "toggle")\n')
            sleep_ms(500)
    except KeyboardInterrupt:
        pass

    # clean on exit
    uart.close()
