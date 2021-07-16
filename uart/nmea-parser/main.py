import time
from machine import Pin, UART


# some const
NMEA_SYS_CODE = {'BD': 'beidou', 'GA': 'galileo', 'GB': 'beidou',
                 'GN': 'gps+glonass', 'GP': 'gps', 'GL': 'glonass'}

# some vars
uart_id = 1
baudrate = 9600
tx_pin = Pin(4, Pin.IN)
rx_pin = Pin(5, Pin.IN)
uart = UART(uart_id, baudrate, tx=tx_pin, rx=rx_pin)
rx_buf= bytes()


# main loop
while True:
    # add new available rx data to buffer
    rx_buf += uart.read(uart.any())
    # process all NMEA sentences in buffer
    while True:
        # extract sentence
        try:
            nmea_s, rx_buf = rx_buf.split(b'\r\n', 1)
            nmea_s = nmea_s.decode()
            # parse sentence
            try:
                # basic check
                if not nmea_s.startswith('$') or len(nmea_s) > 82:
                    raise ValueError()
                # checksum stuff
                nmea_body, nmea_checksum = nmea_s[1:].split('*')
                # compute
                csum = 0
                for char in nmea_body:
                    csum ^= ord(char)
                # check it
                if csum != int(nmea_checksum, 16):
                    raise ValueError()
                # sentence type
                nmea_body = nmea_body.upper()
                nmea_head, *nmea_items = nmea_body.split(',')
                nmea_origin = nmea_head[:2]
                nmea_type = nmea_head[2:]
                nmea_sys = NMEA_SYS_CODE.get(nmea_origin, 'unknown')
                # dump
                print('origin: %s sys: %s type: %s items: %s' % (nmea_origin, nmea_sys, nmea_type, nmea_items))
            except ValueError:
                continue
        except ValueError:
            break
    # limit buffer growth
    rx_buf = rx_buf[-256:]
    # simulate heavy load
    time.sleep(.2)
