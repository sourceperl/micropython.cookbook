""" A basic BLE advertissing sample, broadcasts temperature and humidity (simulated). """

import bluetooth
from micropython import const
import random
import struct
import time


# some const
SENSOR_NAME = const('My sensor')
FLAG_BROADCAST = const(0x01)
BR_EDR_NOT_SUPPORTED = const(0x04)
AD_TYPE_SVC_LIST = const(0x03)
AD_TYPE_SVC_DATA = const(0x16)
UUID_SVC_ENV = const(0x181A)
UUID_CHAR_TEMP = const(0x2a6e)
UUID_CHAR_HUM = const(0x2a6f)

# init BLE
ble = bluetooth.BLE()
ble.active(True)

# build adv payload
adv_data = bytearray()
# advertising flag (here ble only)
adv_data += struct.pack('BBB', 2, FLAG_BROADCAST, BR_EDR_NOT_SUPPORTED)
# sensor name
adv_data += struct.pack('BB', len(SENSOR_NAME) + 1, 0x09) + SENSOR_NAME

while True:
    # services data
    adv_svc_data = bytearray()
    # add temperature
    temp = 25.0 + random.random() * 2
    temp_data = struct.pack('<Hh', UUID_CHAR_TEMP, int(temp*100))
    adv_svc_data += struct.pack('BB', len(temp_data) + 1, AD_TYPE_SVC_DATA) + temp_data
    # add humidity
    hum = 44.0 + random.random() * 2
    hum_data = struct.pack('<HH', UUID_CHAR_HUM, int(hum*100))
    adv_svc_data += struct.pack('BB', len(hum_data) + 1, AD_TYPE_SVC_DATA) + hum_data

    # advertising every 250ms
    ble.gap_advertise(250_000, adv_data=adv_data+adv_svc_data, connectable=False)

    # update every 1s
    time.sleep(1.0)
