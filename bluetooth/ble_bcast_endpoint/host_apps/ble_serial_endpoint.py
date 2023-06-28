#!/usr/bin/env python3

""" Relay json message from serial to redis DB. """

import argparse
from datetime import datetime
import json
import logging
import sys
import serial
import redis


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
    serial_p.flush()

    # serial message processing loop
    while True:
        try:
            # read serial message as a json struct
            msg = serial_p.readline().strip().decode()
            logging.debug(f'rx message: {msg}')
            # parse serial message
            msg_as_dict = json.loads(msg)
            # add "receive_dt"
            receive_dt = datetime.now().astimezone().isoformat()
            msg_as_dict['receive_dt'] = receive_dt
            # try to find a BLE device name from its current device id
            device_id = msg_as_dict['id']
            device_name = None
            hash_name = red_cli.hget('ble-names-by-ids', device_id)
            if hash_name:
                device_name = hash_name.decode()
            # update redis json key
            # priority to key name "ble-data-js:name" if name is set, else use "ble-data-js:id"
            redis_key = f'ble-data-js:{device_name or device_id}'
            redis_value = json.dumps(msg_as_dict)
            logging.debug(f'redis set key {redis_key}: {redis_value}')
            red_cli.set(redis_key, redis_value, ex=3600)
            # when name is set for this id, remove old "ble-data-js:id" key
            if device_name:
                red_cli.delete(f'ble-data-js:{device_id}')
            # update last seen redis hash
            red_cli.hset(f'ble-last-seen-by-ids', device_id, receive_dt)
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
