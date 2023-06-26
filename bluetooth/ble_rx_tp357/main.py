""" Collect ThermoPro TP357 bluetooth data (https://buythermopro.com/product/tp357/).

Export advertising elements as json messages.
"""

from micropython import const
from ubinascii import hexlify
import ubluetooth
import ujson
from ustruct import unpack
import utime


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
        # scan items
        addr_type, addr_b, adv_type, rssi, adv_data = data
        name = decode_short_name(adv_data) or decode_compl_name(adv_data)
        # init an export dict
        export_d = {}
        # limit to TP357 messages
        if name.startswith('TP357'):
            # test "manufacturer specific data" is set
            mfr_data_l = decode_field(adv_data, ADV_MANUF_SPEC_DATA)
            if len(mfr_data_l) > 0:
                # populate export_d with data of first MSD field
                mfr_data = mfr_data_l[0]
                (temp, hum) = unpack('<hB', mfr_data[1:4])[:2]
                export_d['temp_c'] = float(temp/10)
                export_d['hum_p'] = int(hum)
        # if export dict is set
        if export_d:
            # add mandatory fields
            export_d['name'] = name
            export_d['addr'] = hexlify(bytes(addr_b), '-').decode()
            export_d['rssi'] = rssi
            # export adv dict as a json message
            print(ujson.dumps(export_d))


if __name__ == '__main__':
    # init BLE
    ble = ubluetooth.BLE()
    ble.active(True)

    # init BLE scan
    ble.irq(on_ble_event)

    while True:
        # start a BLE scan cycle
        ble.gap_scan(0, 30_000, 30_000)

        # 2mn scan, ensure to release on abort
        try:
            utime.sleep(120.0)
        finally:
            # stop scan
            ble.gap_scan(None)
