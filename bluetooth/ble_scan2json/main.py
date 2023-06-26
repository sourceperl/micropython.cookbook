""" A basic micropython BLE scanner on a Pico W.

Export advertising elements as json messages.
"""

import ubluetooth
import ujson
from binascii import hexlify
from micropython import const
import time


# some const
IRQ_SCAN_RESULT = const(0x05)
ADV_TYPE_SHORT_NAME = const(0x08)
ADV_TYPE_COMPL_NAME = const(0x09)
ADV_MANUF_SPEC_DATA = const(0xff)


# some func
def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2: i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_short_name(payload):
    n = decode_field(payload, ADV_TYPE_SHORT_NAME)
    return str(n[0], 'utf8') if n else ''


def decode_compl_name(payload):
    n = decode_field(payload, ADV_TYPE_SHORT_NAME)
    return str(n[0], 'utf8') if n else ''


def on_ble_event(event, data):
    if event == IRQ_SCAN_RESULT:
        addr_type, addr_b, adv_type, rssi, adv_data = data
        # to avoid flood, limit to nearby devices
        if rssi > -70:
            # init adv dict
            adv_d = {}
            # mandatory fields
            adv_d['addr'] = hexlify(bytes(addr_b), '-').decode()
            adv_d['rssi'] = rssi
            adv_d['name'] = decode_short_name(adv_data) or decode_compl_name(adv_data)
            # optional fields
            # "manufacturer specific data"
            manuf_data_l = decode_field(adv_data, 0xff)
            if manuf_data_l:
                adv_d['manuf_data'] = []
                for manuf_data in manuf_data_l:
                    adv_d['manuf_data'].append(hexlify(manuf_data, '-'))
            # export adv dict as a json message
            print(ujson.dumps(adv_d))


if __name__ == '__main__':
    # init BLE
    ble = ubluetooth.BLE()
    ble.active(True)

    # start BLE scan
    ble.irq(on_ble_event)
    ble.gap_scan(0, 30_000, 30_000)

    # 2mn scan, ensure to release on abort
    try:
        time.sleep(120.0)
    finally:
        # stop scan
        ble.gap_scan(None)
