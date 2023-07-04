#!/usr/bin/env python3

"""
A basic multi-threaded HTTP server with a json endpoint.

Test with:
curl -v -d '{"foo": "hello"}' -H "Content-Type: application/json" -X POST http://localhost:8080/api/test
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
import json
import logging
import socket
from threading import Thread
import time
from typing import Any


# some class
class HttpSrv:
    """A multi-threaded HTTP server for share camera image."""

    class HandleRequests(BaseHTTPRequestHandler):
        """Custom HTTP handler"""

        def version_string(self) -> str:
            """Replace default server banner."""
            return 'my server'

        # def log_message(self, format: str, *args: Any) -> None:
        #     """Replace log_message to turn off log msg."""
        #     return None

        def do_GET(self):
            """Process HTTP GET request."""
            # catch socket errors
            try:
                # process every HTTP GET endpoints
                if self.path == '/time':
                    # headers
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    # body
                    self.wfile.write(f'timestamp is {round(time.time())}\n'.encode('utf-8'))
                # on other path, nothing for you here
                else:
                    # return HTTP 404 page not found
                    self.send_response(404)
                    self.end_headers()
            except socket.error:
                pass

        def do_POST(self):
            """Process HTTP POST request."""
            # catch socket errors
            try:
                # api "test" endpoint
                if self.path == '/api/test':
                    # this endpoint only processes json messages
                    if self.headers.get('Content-Type') == 'application/json':
                        content_length = int(self.headers.get('Content-Length', 0))
                        raw_js_data = self.rfile.read(content_length)
                        try:
                            js_data = json.loads(raw_js_data)
                            logging.info(f"json = {js_data}")
                            # HTTP code "OK"
                            self.send_response(200)
                            response_d = dict(status='success')
                        except KeyError as e:
                            # Key not in json dict: HTTP code "Bad Request"
                            self.send_response(400)
                            response_d = dict(status='error', message=f'mandatory key "{e}" not found')
                        except json.JSONDecodeError as e:
                            # Invalid json data: HTTP code "Bad Request"
                            self.send_response(400)
                            response_d = dict(status='error', message=f'invalid json data: {e}')
                    else:
                        # Unsupported Content-Type: HTTP code "Bad Request"
                        self.send_response(400)
                        response_d = dict(status='error', message=f'Unsupported Content-Type')
                    # send response
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    # body
                    self.wfile.write(json.dumps(response_d).encode() + b'\n')
                # on unknown path
                else:
                    # return HTTP 404 page not found
                    self.send_response(404)
                    self.end_headers()
            except socket.error:
                pass

    def __init__(self, port: int = 8080, bind: str = 'localhost'):
        # public
        self.port = port
        self.bind = bind
        # private
        self._http_srv = None
        self._http_srv_th = None

    def start(self, block=False):
        """Start HTTP server as a thread."""
        # autodetect IPv6 address
        try:
            ipv6 = ip_address(self.bind).version == 6
        except ValueError:
            ipv6 = False
        # add IPv6 support to ThreadingHTTPServer if needed
        if ipv6:
            ThreadingHTTPServer.address_family = socket.AF_INET6
        #  init HTTP server
        ThreadingHTTPServer.allow_reuse_address = True
        self._http_srv = ThreadingHTTPServer((self.bind, self.port), self.HandleRequests)
        # pass a_thing to HandleRequests (available at HandleRequests.server.a_thing)
        # for example self._http_srv.a_thing = self.a_thing
        # start server (with or without blocking)
        if block:
            # start server and block here
            self._http_srv.serve_forever()
        else:
            # start server in a separate thread
            self._http_srv_th = Thread(target=self._http_srv.serve_forever, daemon=True)
            self._http_srv_th.start()

    def stop(self):
        """Stop HTTP server thread."""
        self._http_srv.shutdown()
        self._http_srv.server_close()


# main program
if __name__ == '__main__':
    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help='set debug mode')
    args = parser.parse_args()
    # logging setup
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level)
    logging.info('start HTTP server')
    # init and start HTTP server
    srv = HttpSrv(bind='0.0.0.0')
    srv.start(block=True)
