import network
import tinyweb
from machine import Pin
from utime import sleep
from private_data import WIFI_SSID, WIFI_KEY


# define an access point, name it and then make it active
ap = network.WLAN(network.AP_IF)
ap.config(essid=WIFI_SSID, password=WIFI_KEY)
ap.active(True)

# wait until it is active
while ap.active == False:
    pass
print('access point active')

# print out IP information
print(ap.ifconfig())

# define on-board LED
led = Pin('LED', Pin.OUT)

# start up a tiny web server
app = tinyweb.webserver()

# serve a simple Hello World! response when / is called
# and turn the LED on/off using toggle()
@app.route('/')
async def index(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
    # Send actual HTML page
    await response.send('<html><body><h1>Hello, world!</h1></body></html>\n')    
    led.toggle()

@app.route('/on')
async def on(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
    # Send actual HTML page
    await response.send('<html><body><h1>LED is on</h1></body></html>\n')
    led.on()

@app.route('/off')
async def off(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
    # Send actual HTML page
    await response.send('<html><body><h1>LED is off</h1></body></html>\n')
    led.off()


# Run the web server as the sole process
app.run(host="0.0.0.0", port=80)
