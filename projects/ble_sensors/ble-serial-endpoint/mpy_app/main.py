""" Collect data from BLE sensors:

- ThermoPro TP357 indoor hygrometer thermometer (https://buythermopro.com/product/tp357/)
- SwitchBot W3400010 outdoor hygrometer thermometer

Export advertising elements as json messages.

Test on MicroPython v1.24.1 on 2024-11-29; Raspberry Pi Pico W with RP2040
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
ADV_TYPE_SERVICE_DATA = const(0x16)
ADV_MANUF_SPEC_DATA = const(0xff)


# some func
def decode_field(payload: bytes, adv_type: int) -> list:
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2: i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_short_name(payload: bytes) -> str:
    n = decode_field(payload, ADV_TYPE_SHORT_NAME)
    return str(n[0], 'utf8') if n else ''


def decode_compl_name(payload: bytes) -> str:
    n = decode_field(payload, ADV_TYPE_COMPL_NAME)
    return str(n[0], 'utf8') if n else ''


def on_ble_event(event: int, data: list):
    if event == IRQ_SCAN_RESULT:
        # scan items
        addr_type, addr_b, adv_type, rssi, adv_data = data
        bd_addr = addr_b.hex('-')
        # extract mandatory fields
        name = decode_short_name(adv_data) or decode_compl_name(adv_data)
        manuf_data_l = decode_field(adv_data, ADV_MANUF_SPEC_DATA)
        # init an export dict
        export_d = OrderedDict()
        # TP357 messages
        if name.startswith('TP357'):
            # test "manufacturer specific data" is set
            if manuf_data_l and len(manuf_data_l[0]) == 6:
                # populate export_d with data of first manuf data field
                manuf_data = manuf_data_l[0]
                export_d['model'] = 'tp357'
                export_d['id'] = bd_addr
                (temp, hum) = unpack('<hB', manuf_data[1:4])[:2]
                export_d['temp_c'] = float(temp/10)
                export_d['hum_p'] = int(hum)
        # W3400010 messages
        # company ID == 0x0969 (Woan technology)
        elif manuf_data_l and len(manuf_data_l[0]) == 14 and manuf_data_l[0][:2] == b'\x69\x09':
            export_d['model'] = 'w3400010'
            export_d['id'] = bd_addr
            # add temp and hum data from first manuf data field
            manuf_data = manuf_data_l[0]
            if manuf_data[11] < 0x80:
                export_d['temp_c'] = -manuf_data[11] + manuf_data[10] / 10.0
            else:
                export_d['temp_c'] = manuf_data[11] - 0x80 + manuf_data[10] / 10.0
            export_d['hum_p'] = manuf_data[12]
            # extract specific field
            service_data_l = decode_field(adv_data, ADV_TYPE_SERVICE_DATA)
            if service_data_l:
                service_data = service_data_l[0]
                if len(service_data) == 5 and service_data[:2] == b'\x3d\xfd':
                    export_d['batt_p'] = service_data[4] & 0x7f
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
