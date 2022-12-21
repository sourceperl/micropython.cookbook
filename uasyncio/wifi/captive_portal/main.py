"""
A captive web portal test on Pico W.

- create an open wifi access-point.
- start a web server.
- redirect all DNS requests to this web server.
"""

from machine import Pin, ADC
import network
import uasyncio as aio
import usocket
import rp2
from lib import tinyweb

# some const
HOSTNAME = 'pico-w'
DEBUG_STA_MODE = False


# some class
class ShareList:
    counter = 0
    volts = 0.0
    temperature = 0.0
    led_pin = Pin('LED', Pin.OUT)


# start up network in access point mode (without password)
rp2.country('FR')
if DEBUG_STA_MODE:
    from private_data import WIFI_SSID, WIFI_KEY
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # disable power-save mode (more responsive)
    wlan.config(pm=0xa11140)
    wlan.connect(WIFI_SSID, WIFI_KEY)
else:
    wlan = network.WLAN(network.AP_IF)
    wlan.config(essid='Pico W')
    wlan.config(security=False)
    wlan.active(True)

# wait access-point is ready
while not wlan.isconnected() if DEBUG_STA_MODE else not wlan.active:
    pass
ap_ip_address = wlan.ifconfig()[0]
print(f'access point active at @{ap_ip_address}')


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
web_srv = tinyweb.webserver(debug=True)


# serve a simple Hello World! response when / is called
# and turn the LED on/off using toggle()
@web_srv.route('/', save_headers=['Host'])
async def index(request, response):
    # redirect for bad hostname
    if DEBUG_STA_MODE or request.headers.get(b'Host', b'').decode() == HOSTNAME:
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


# API: export ShareList values
@web_srv.resource('/api/export.json')
def export_json(_data):
    return {'temperature': round(ShareList.temperature, 2),
            'counter': ShareList.counter,
            'led_status': ShareList.led_pin.value()}


# API: onboard LED control
@web_srv.resource('/api/led', method='POST')
def led_control(data):
    led_status = data.get('status', '')
    if led_status == 'on':
        ShareList.led_pin.value(True)
        return {'message': 'LED is turn on'}
    elif led_status == 'off':
        ShareList.led_pin.value(False)
        return {'message': 'LED is turn off'}
    return {'message': 'error (status must be set to on or off)'}


# redirect (301) the various endpoints that OSes use to check connectivity
if not DEBUG_STA_MODE:
    @web_srv.catchall()
    async def catchall(request, response):
        await response.redirect(f'http://{HOSTNAME}/')


# tinyweb automatically adds the web server to the event loop
# also web_srv will be run as a coroutine by loop.forever() at end
web_srv.run(host='0.0.0.0', port=80, loop_forever=False)


# main task
async def feed_list_task():
    while True:
        ShareList.counter += 1
        ShareList.temperature = 27 - ((ADC(4).read_u16() * 3.3 / 65535) - 0.706) / 0.001721
        await aio.sleep_ms(1_000)


# create asyncio task and run it (web_srv already created)
loop = aio.get_event_loop()
if not DEBUG_STA_MODE:
    loop.create_task(dns_srv_task(ip_address=ap_ip_address))
loop.create_task(feed_list_task())
loop.run_forever()
