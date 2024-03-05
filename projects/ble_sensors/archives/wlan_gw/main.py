""" Send a json message with POST method to an HTTP server. """

import gc
from micropython import const
import network
import rp2
import ubluetooth
from ucollections import OrderedDict
import ujson
import urequests
from ustruct import unpack
from utime import sleep_ms
from private_data import WIFI_SSID, WIFI_KEY


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
        # free memory (avoid ENOMEM)
        gc.collect()
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
                (temp, hum) = unpack('<hB', msd[1:4])[:2]
                export_d['temp_c'] = float(temp/10)
                export_d['hum_p'] = int(hum)
        # W3400010 messages
        # company ID == 0x0969 (Woan technology)
        elif msd[:2] == b'\x69\x09':
            if len(msd) == 14:
                export_d['model'] = 'w3400010'
                export_d['debug'] = msd[8:10].hex('-')
                if msd[11] < 0x80:
                    export_d['temp_c'] = -msd[11] + msd[10] / 10.0
                else:
                    export_d['temp_c'] = msd[11] - 0x80 + msd[10] / 10.0
                export_d['hum_p'] = msd[12]
                # export_d['batt_p'] = msd[8] & 0x7f
        else:
            export_d['model'] = 'obni'
            export_d['debug'] = msd.hex('-')
        # if export dict is set
        if export_d:
            # build json dict with mandatory fields ahead
            to_js_d = OrderedDict()
            to_js_d['bd_addr'] = bd_addr
            to_js_d['rssi'] = rssi
            to_js_d['id'] = export_d.pop('id', None) or bd_addr
            to_js_d['model'] = export_d.pop('model')
            # add optional fields
            if name:
                to_js_d['name'] = name
            to_js_d.update(export_d)
            # export adv dict as a json (compact) message
            js_msg = ujson.dumps(to_js_d, separators=(',', ':'))
            # print(js_msg)
            # publish json message with HTTP POST
            try:
                r = urequests.post('http://192.168.0.28:8080/api/test', json=js_msg, timeout=4.0)
                print(f'HTTP status: {r.status_code}')
            except (OSError, ValueError) as e:
                print(f'HTTP POST status: error {e!r}')


if __name__ == '__main__':
    # init wlan
    rp2.country('FR')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # disable power-saving mode
    wlan.config(pm=0xa11140)
    # wlan connect
    wlan.connect(WIFI_SSID, WIFI_KEY)

    # init BLE
    ble = ubluetooth.BLE()
    ble.active(True)
    # init BLE scan
    ble.irq(on_ble_event)

    # wait WLAN up
    if not wlan.isconnected():
        sleep_ms(4_000)

    # check network status
    if wlan.status() == network.STAT_GOT_IP:
        print(f'wifi connected (@IP {wlan.ifconfig()[0]})')

    while True:
        # start a BLE scan cycle
        ble.gap_scan(0, 30_000, 30_000)

        # 2mn scan, ensure to release on abort
        try:
            sleep_ms(120_000)
        finally:
            # stop scan
            ble.gap_scan(None)
