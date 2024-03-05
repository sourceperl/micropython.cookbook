#!/usr/bin/env python3

""" Relay BLE data from redis to influxdb. """

import argparse
from datetime import datetime
import json
import logging
import sys
import time
import urllib.error
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import redis


# some const
BLE_FIELDS_FOR_DB = [('rssi', int), ('temp_c', float), ('hum_p', int)]
INFLUX_DB = 'mydb'
INFLUX_URL = 'http://localhost:8086/api/v2/write'


# parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
args = parser.parse_args()
# logging setup
level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level)
logging.info('start influxdb ble broadcast relay')

try:
    # init redis client
    red_cli = redis.StrictRedis()

    # processing loop
    while True:
        try:
            # search for data of all available BLE sensors
            for key_name in red_cli.keys('ble-js:*'):
                # extract sensor name from redis key "ble-js:[my_name]"
                key_name = key_name.decode()
                sensor_name = key_name.split(':')[-1]
                # search json struct for this key
                js_msg = red_cli.get(key_name)
                if js_msg:
                    js_msg_str = js_msg.decode()
                    ble_d = json.loads(js_msg_str)
                    # get a timestamp (with s precision) from mandatory field "receive_dt"
                    timestamp_s = round(datetime.fromisoformat(ble_d.get('receive_dt')).timestamp())
                    # format line protocol string for influxdb update
                    post_line_head = f'ble_sensors,sensor={sensor_name}'
                    post_line_values = ''
                    for field_name, field_type in BLE_FIELDS_FOR_DB:
                        f_value = ble_d.get(field_name)
                        if f_value is not None:
                            if post_line_values:
                                post_line_values += ','
                            post_line_values += f'{field_name}={field_type(f_value)}'
                    post_line = f'{post_line_head} {post_line_values} {timestamp_s}'
                    # update influxdb
                    url = f"{INFLUX_URL}?{urlencode(dict(bucket=INFLUX_DB, precision='s'))}"
                    logging.debug(f'POST "{post_line}" to "{url}"')
                    urlopen(Request(url, data=post_line.encode()), timeout=4.0)
        except redis.RedisError as e:
            logging.warning(f'redis error: {e!r}')
        except urllib.error.URLError as e:
            logging.warning(f'urllib error occur: {e!r}')
        except (ValueError, TypeError) as e:
            logging.warning(f'parsing error: {e!r}')
        # wait next refresh
        time.sleep(60.0)
except KeyboardInterrupt:
    sys.exit(0)
except redis.RedisError as e:
    logging.error(f'redis error: {e!r}')
    sys.exit(1)
