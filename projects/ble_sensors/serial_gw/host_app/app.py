#!/usr/bin/env python3

""" Relay json message from serial to redis DB. """

import argparse
from datetime import datetime
import json
import logging
import sys
import serial
import redis
from conf.private_data import ID_NAME_DICT


# parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('port', nargs='?', default='/dev/ttyACM0', help='serial port (default is "/dev/ttyACM0")')
parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
args = parser.parse_args()
# logging setup
level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level)
logging.info('start ble broadcast endpoint host app')

try:
    # init redis client and serial port
    red_cli = redis.StrictRedis()
    serial_p = serial.Serial(port=args.port)
    serial_p.reset_input_buffer()

    # serial message processing loop
    while True:
        try:
            # read serial message as a json struct
            js_msg = serial_p.readline().strip().decode()
            rx_dt = datetime.now().astimezone()
            logging.debug(f'rx message: {js_msg}')
            # convert rx json msg to dict
            msg_d = json.loads(js_msg)
            # add "receive_dt" field
            msg_d['receive_dt'] = rx_dt.isoformat()
            # try to find a BLE device name from its current device id
            device_id = msg_d['id']
            try:
                device_name = ID_NAME_DICT[device_id]
            except KeyError:
                device_name = device_id
            # update redis json key
            # priority to key name "ble-data-js:name" if name is set, else use "ble-data-js:id"
            redis_key = f'ble-js:{device_name}'
            msg_d_as_js = json.dumps(msg_d)
            logging.debug(f'redis set key {redis_key}: {msg_d_as_js}')
            red_cli.set(redis_key, msg_d_as_js, ex=3600)
            # update last seen redis hash
            red_cli.hset(f'ble-last-seen-by-ids', device_id, rx_dt.isoformat())
        except redis.RedisError as e:
            logging.warning(f'redis error: {e!r}')
        except (ValueError, KeyError) as e:
            logging.warning(f'parsing error: {e!r}')
except KeyboardInterrupt:
    sys.exit(0)
except serial.SerialException as e:
    logging.error(f'serial error: {e!r}')
    sys.exit(1)
except redis.RedisError as e:
    logging.error(f'redis error: {e!r}')
    sys.exit(2)
