"""
A captive web portal test on Pico W.

- create an open wifi access-point.
- start a web server.
- redirect all DNS requests to this web server.
"""

from machine import Pin
import network
import uasyncio as aio
import usocket
import gc
from lib import tinyweb

# some const
HOSTNAME = 'pico-w'
# PINs available for test
WEB_PINS_D = {28: 'GPIO28'}

# start up network in access point mode (without password)
wlan = network.WLAN(network.AP_IF)
wlan.config(essid='Pico W')
wlan.config(security=False)
wlan.active(True)

# wait access-point is ready
while not wlan.active:
    pass
ap_ip_address = wlan.ifconfig()[0]
print(f'access point active at @{ap_ip_address}')

# define on-board LED
led = Pin('LED', Pin.OUT)


# DNS server task: resolve all DNS requests with AP ip_address
async def dns_srv_task(ip_address='192.168.4.1'):
    # init DNS socket
    dns_sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
    dns_sock.setblocking(False)
    dns_sock.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
    dns_sock.bind(usocket.getaddrinfo('0.0.0.0', 53, 0, usocket.SOCK_DGRAM)[0][-1])
    # process DNS requests
    while True:
        try:
            yield aio.core._io_queue.queue_read(dns_sock)
            request, client = dns_sock.recvfrom(256)
            # request id
            response = request[:2]
            # response flags
            response += b'\x81\x80'
            # qd/an count
            response += request[4:6] + request[4:6]
            # ns/ar count
            response += b'\x00\x00\x00\x00'
            # original request body
            response += request[12:]
            # pointer to domain name at byte 12
            response += b'\xC0\x0C'
            # type and class (A record / IN class)
            response += b'\x00\x01\x00\x01'
            # time to live 60 seconds
            response += b'\x00\x00\x00\x3C'
            # response length (4 bytes = 1 ipv4 address)
            response += b'\x00\x04'
            # ip address parts
            response += bytes(map(int, ip_address.split('.')))
            dns_sock.sendto(response, client)
        except Exception as e:
            print(e)


# start up a tiny web server
web_srv = tinyweb.webserver()


# serve a simple Hello World! response when / is called
# and turn the LED on/off using toggle()
@web_srv.route('/', save_headers=['Host'])
async def index(request, response):
    # redirect for bad hostname
    if request.headers.get(b'Host', b'').decode() == HOSTNAME:
        await response.send_file('static/index.html')
    else:
        await response.redirect(f'http://{HOSTNAME}/')


@web_srv.route('/css/<fn>')
async def files_css(request, response, fn):
    await response.send_file(f'static/css/{fn}.gz', content_type='text/css', content_encoding='gzip')


@web_srv.route('/img/<fn>')
async def files_img(request, response, fn):
    await response.send_file(f'static/img/{fn}', content_type='image/jpeg')


@web_srv.route('/js/<fn>')
async def files_js(request, response, fn):
    await response.send_file(f'static/js/{fn}.gz', content_type='application/javascript', content_encoding='gzip')


@web_srv.route('/on')
async def on(request, response):
    led.on()
    await response.start_html()
    await response.send('<html><body><h1>LED is on</h1></body></html>')


@web_srv.route('/off')
async def off(request, response):
    led.off()
    await response.start_html()
    await response.send('<html><body><h1>LED is off</h1></body></html>')


# redirect (301) the various endpoints that OSes use to check connectivity
@web_srv.catchall()
async def catchall(request, response):
    await response.redirect(f'http://{HOSTNAME}/')


# RESTAPI: System status
class Status():

    def get(self, data):
        mem = {'mem_alloc': gc.mem_alloc(),
               'mem_free': gc.mem_free(),
               'mem_total': gc.mem_alloc() + gc.mem_free()}
        ap_if = network.WLAN(network.AP_IF)
        ifconfig = ap_if.ifconfig()
        net = {'ip': ifconfig[0],
               'netmask': ifconfig[1],
               'gateway': ifconfig[2],
               'dns': ifconfig[3]}
        return {'memory': mem, 'network': net}


# RESTAPI: GPIO status
class GPIOList():

    def get(self, data):
        res = []
        for p, d in WEB_PINS_D.items():
            val = Pin(p).value()
            res.append({'gpio': p, 'nodemcu': d, 'value': val})
        return {'pins': res}


# REST API: GPIO controller: turn PINs on/off
class GPIO():

    def put(self, data, pin):
        # Check input parameters
        if 'value' not in data:
            return {'message': '"value" is requred'}, 400
        # Check pin
        pin = int(pin)
        if pin not in WEB_PINS_D:
            return {'message': 'no such pin'}, 404
        # Change state
        val = int(data['value'])
        Pin(pin).value(val)
        return {'message': 'changed', 'value': val}


# set PINS to OUT mode
for p, d in WEB_PINS_D.items():
    Pin(p, Pin.OUT)
# build REST API tree
web_srv.add_resource(Status, '/api/status')
web_srv.add_resource(GPIOList, '/api/gpio')
web_srv.add_resource(GPIO, '/api/gpio/<pin>')
# tinyweb automatically adds the web server to the event loop
# also web_srv will be run as a coroutine by loop.forever() at end
web_srv.run(host='0.0.0.0', port=80, loop_forever=False)


# main task
async def counter_task():
    i = 0
    while True:
        i += 1
        # print(f'{i=}')
        await aio.sleep_ms(1_000)


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(dns_srv_task(ip_address=ap_ip_address))
loop.create_task(counter_task())
loop.run_forever()
