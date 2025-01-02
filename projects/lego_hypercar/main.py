""" A BLE UART peripheral, command a pico W built-in LED with on, off or toggle commands. """

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

    def update(self):
        """Call regulary by main thread to process bluetooth I/O."""
        # telemetry
        # self.write('telemetry message\n')
        # process incoming packets
        if self.any():
            # all available bytes
            rx_data = self.read()
            # parse data
            # print(f'raw: {rx_data}')
            i = 0
            while i < len(rx_data):
                try:
                    #  search packet prefix '!'
                    if rx_data[i] == ord('!'):
                        # 2nd char is command id
                        if rx_data[i+1] == ord('B'):
                            self._pkt_b(rx_data[i:i+5])
                    # next char
                    i += 1
                except IndexError:
                    break

    def _pkt_crc_ok(self, pkt: bytearray):
        """Return True if packet have valid CRC."""
        _sum = 0
        for c in pkt:
            _sum += c
        return _sum & 0x7f == 0x7f

    def _pkt_b(self, pkt: bytearray):
        """Process B packet."""
        # check len
        if len(pkt) != 5:
            return
        # check CRC
        if not self._pkt_crc_ok(pkt):
            print('bad CRC')
            return
        # decode button infos
        try:
            btn_id = int(chr(pkt[2]))
            btn_released = pkt[3] == ord('0')
            btn_pressed = pkt[3] == ord('1')
        except ValueError:
            return
        # buttons handlers
        if btn_pressed:
            self._on_btn_pressed(btn_id)
        if btn_released:
            self._on_btn_released(btn_id)

    def _on_btn_pressed(self, btn_id: int):
        print(f'btn {btn_id}: pressed')

    def _on_btn_released(self, btn_id: int):
        print(f'btn {btn_id}: relassed')


if __name__ == "__main__":
    # I/O init
    led = Pin('LED', Pin.OUT)
    # bluetooth init
    ble = bluetooth.BLE()
    uart = BLE_UART(ble, name='LEGO_CAR')
    # uart.on_write = lambda: print('rx: ', uart.read())
    # main loop (exit with ctrl-c)
    try:
        while True:
            uart.update()
    except KeyboardInterrupt:
        pass

    # clean on exit
    uart.close()
