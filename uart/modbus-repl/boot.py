from utime import sleep, ticks_us, ticks_diff
from machine import Pin, UART
from math import ceil


# some vars
uart_id = 1
tx_pin = Pin(4, Pin.IN)
rx_pin = Pin(5, Pin.IN)


def crc16(data: bytearray):
    crc = 0xFFFF
    for byte in bytearray(data):
        next_byte = byte
        crc ^= next_byte
        for i in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc


def frame2hex(frame: bytearray): 
    return '-'.join(['%02X' % b for b in frame])


def check_crc_ok(frame: bytearray): 
    try:
        assert len(frame) > 2
        cp_crc = crc16(frame[:-2])
        rx_crc = int.from_bytes(frame[-2:], 'little')
        return cp_crc == rx_crc
    except:
        return False


def dump(baudrate=9600, parity=None, stop=1, eof_ms=None, sum=False):
    # check params
    if not (300 < baudrate <= 115_200):
        raise ValueError('valid baudrate is between 300 to 115200 bauds')        
    if parity not in (None, 0, 1):
        raise ValueError('parity can be None, 0 (even) or 1 (odd)')
    if stop not in (1, 2):
        raise ValueError('stop (number of stop bits) can be 1 or 2')
    if eof_ms is None:
        # automatic value :
        # end of frame (eof) is a silence on rx line > 3.5 * byte transmit time
        rx_silence_ms = ceil(max(1.2 * 3.5 * (1000/(baudrate/10)), 10.0))
        print('eof detection = {:d} ms (can be overide by "eof_ms" arg)\n'.format(rx_silence_ms))
    else:
        # manual override
        if not (0 < eof_ms <= 1000):
            raise ValueError('eof_ms must be between 0 to 1000 ms or None (automatic)')
        rx_silence_ms = eof_ms
    # init UART
    uart = machine.UART(uart_id, baudrate, tx=tx_pin, rx=rx_pin, bits=8, parity=parity, stop=stop)
    # flush buffer after UART startup
    sleep(0.5)
    uart.read(uart.any())
    # main loop
    while True:
        rx_b = bytearray()
        rx_t = ticks_us()
        # frame receive loop
        while True:
            # on data available
            if uart.any() > 0:
                # read data block with time of arrival
                rx_t = ticks_us()
                rx_b.extend(uart.read(uart.any()))
                # limit buffer size to 256 bytes
                rx_b = rx_b[-256:]
            frame_end = ticks_diff(ticks_us(), rx_t) > rx_silence_ms * 1000
            # out of receive loop if data in buffer and end of frame occur 
            if frame_end and rx_b:
                break
        # check frame
        crc_ok = check_crc_ok(rx_b)
        # dump frame
        frame_dump = '[size {:>3}/CRC {:<3}] '.format(len(rx_b), 'OK' if crc_ok else 'ERR')
        if sum:
            frame_dump += frame2hex(rx_b[:10]) + ('-..' if len(rx_b) > 10 else '')
        else:
            frame_dump += frame2hex(rx_b)
        print(frame_dump)


def help():
    print(open('help.txt', 'r').read())
