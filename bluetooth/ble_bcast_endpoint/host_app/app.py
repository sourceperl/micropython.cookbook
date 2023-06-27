#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
import logging
import sys
import serial
import redis

# some const
REDIS_HASH_KEY = 'ble:devices'

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
            # remove "addr" and add "receive_dt"
            addr = msg_as_dict.pop('addr')
            msg_as_dict['receive_dt'] = datetime.now().astimezone().isoformat()
            # update redis hash
            red_cli.hset(REDIS_HASH_KEY, addr, json.dumps(msg_as_dict))
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
