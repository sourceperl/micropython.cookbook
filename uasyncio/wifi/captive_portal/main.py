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
import tinyweb


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
            # origional request body
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
@web_srv.route('/')
async def index(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
    # Send actual HTML page
    await response.send('<html><body><h1>Hello, world!</h1></body></html>\n')    
    led.toggle()

@web_srv.route('/on')
async def on(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
    # Send actual HTML page
    await response.send('<html><body><h1>LED is on</h1></body></html>\n')
    led.on()

@web_srv.route('/off')
async def off(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
    # Send actual HTML page
    await response.send('<html><body><h1>LED is off</h1></body></html>\n')
    led.off()

# tinyweb automatically adds the web server to the event loop
# also web_srv will be run as a coroutine by loop.forever() at end
web_srv.run(host='0.0.0.0', port=80, loop_forever=False)


# main task
async def counter_task():
    i = 0
    while True:
        i += 1
        print(f'{i=}')
        await aio.sleep_ms(1_000)


# create asyncio task and run it
loop = aio.get_event_loop()
loop.create_task(dns_srv_task(ip_address=ap_ip_address))
loop.create_task(counter_task())
loop.run_forever()
