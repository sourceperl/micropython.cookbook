""" Collect data from BLE sensors:

- ThermoPro TP357 indoor hygrometer thermometer (https://buythermopro.com/product/tp357/)
- SwitchBot W3400010 outdoor hygrometer thermometer

Export advertising elements as json messages.

Test on MicroPython v1.20.0-198-g0eacdeb1c on 2023-06-13; Raspberry Pi Pico W with RP2040
"""

from micropython import const
import ubluetooth
from ucollections import OrderedDict
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
        bd_addr = addr_b.hex('-')
        name = decode_short_name(adv_data) or decode_compl_name(adv_data)
        msd_l = decode_field(adv_data, ADV_MANUF_SPEC_DATA)
        msd = msd_l[0] if msd_l else b''
        # init an export dict
        export_d = OrderedDict()
        # TP357 messages
        if name.startswith('TP357'):
            # test "manufacturer specific data" is set
            if len(msd) == 6:
                # populate export_d with data of first MSD field
                export_d['model'] = 'tp357'
                export_d['id'] = bd_addr
                (temp, hum) = unpack('<hB', msd[1:4])[:2]
                export_d['temp_c'] = float(temp/10)
                export_d['hum_p'] = int(hum)
        # W3400010 messages
        # company ID == 0x0969 (Woan technology)
        elif msd[:2] == b'\x69\x09':
            if len(msd) == 14:
                export_d['model'] = 'w3400010'
                export_d['id'] = bd_addr
                export_d['debug'] = msd[8:10].hex('-')
                if msd[11] < 0x80:
                    export_d['temp_c'] = -msd[11] + msd[10] / 10.0
                else:
                    export_d['temp_c'] = msd[11] - 0x80 + msd[10] / 10.0
                export_d['hum_p'] = msd[12]
                # export_d['batt_p'] = msd[8] & 0x7f
        # if export dict is set
        if export_d:
            # build json dict with mandatory fields ahead
            to_js_d = OrderedDict()
            to_js_d['bd_addr'] = addr_b.hex('-')
            to_js_d['rssi'] = rssi
            to_js_d['id'] = export_d.pop('id')
            to_js_d['model'] = export_d.pop('model')
            # add optional fields
            if name:
                to_js_d['name'] = name
            to_js_d.update(export_d)
            # export adv dict as a json (compact) message
            print(ujson.dumps(to_js_d, separators=(',', ':')))


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
