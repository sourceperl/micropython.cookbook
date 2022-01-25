from utime import sleep, ticks_us, ticks_diff
from machine import Pin, UART


# some vars
uart_id = 1
tx_pin = Pin(4, Pin.IN)
rx_pin = Pin(5, Pin.IN)


# some function
def crc16(frame: bytes):
    crc = 0xFFFF
    for byte in frame:
        crc ^= byte
        for _ in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc


def frame2hex(frame: bytes):
    return '-'.join(['%02X' % b for b in frame])


def dump(baudrate=9600, parity=None, stop=1, eof_ms=None, sum=False):
    # check params
    if not (300 <= baudrate <= 115_200):
        raise ValueError('valid baudrate is between 300 to 115200 bauds')        
    if parity not in (None, 0, 1):
        raise ValueError('parity can be None, 0 (even) or 1 (odd)')
    if stop not in (1, 2):
        raise ValueError('stop (number of stop bits) can be 1 or 2')
    if eof_ms is None:
        # automatic value :
        # end of frame (eof) is a silence on rx line > 3.5 * byte transmit time
        recv_end_ms = round(3.5 * (1000/(baudrate/11)))
        recv_end_ms = max(recv_end_ms, 1)
        print(f'eof detection = {recv_end_ms:d} ms (can be overide by "eof_ms" arg)\n')
    else:
        # manual override
        if not (0 <= eof_ms <= 1000):
            raise ValueError('eof_ms must be between 0 to 1000 ms or None (automatic)')
        recv_end_ms = eof_ms
    # init UART
    uart = machine.UART(uart_id, baudrate, tx=tx_pin, rx=rx_pin, bits=8, parity=parity, stop=stop,
                        rxbuf=256, timeout=0, timeout_char=recv_end_ms)
    # skip first incomplete frame
    while not uart.read():
        pass
    # init
    f_count = 0
    # main loop
    while True:
        # frame receive loop
        while True:
            recv_b = uart.read()
            if recv_b:
                break
        # frame count
        f_count += 1
        # check CRC
        crc_ok = crc16(recv_b) == 0
        # format dump message
        crc_str = 'OK' if crc_ok else 'ERR'
        if sum and len(recv_b) > 20:
            dump_str = frame2hex(recv_b[:20])
            dump_str += '-..'
        else:
            dump_str = frame2hex(recv_b)
        # print dump message
        print(f'[{f_count:>4d}/{len(recv_b):>3}/{crc_str:<3}] {dump_str}')


def help():
    print(open('help.txt', 'r').read())
