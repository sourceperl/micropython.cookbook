""" Simulate a SwitchBot Outdoor Meter BLE transmitter (W3400010) for testing purposes. """

import time

import bluetooth

# init BLE
ble = bluetooth.BLE()
ble.active(True)

# advertise payload
adv_data = bytes.fromhex('0201060FFF6909CD4068A5FD55C20B00805F0006163DFD7700C4')
# advertising every 250ms
ble.gap_advertise(interval_us=250_000, connectable=False, adv_data=adv_data)

while True:
    time.sleep_ms(1_000)
