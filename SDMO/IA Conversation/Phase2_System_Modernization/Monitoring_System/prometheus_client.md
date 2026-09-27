## User Prompt 
I was browsing the internet to find a way to implement a monitoring system for the project, I find out that a standardized way to implement such thing is to use prometheus, could you show me if and how is possible to integrete such tool in this project?

## AI Reply

 This library creates a lightweight web server that runs in the background of your Python app. Every time your application does something (like processing a temperature reading), we will tell the library to update its internal counters.

Here are the specific code changes we are about to make:

1. Update requirements.txt
We will add prometheus-client to the list of required libraries so it installs when we build the Docker container.

2. Instrument src/main.py
We will import the library and define three specific metrics at the top of your file:



```
from prometheus_client import start_http_server, Counter, Gauge
# Define our Metrics
prom_packets = Counter("sdmo_packets_total", "Total packets processed by the Cloud")
prom_temperature = Gauge("sdmo_temperature_celsius", "Current temperature reading")
prom_errors = Counter("sdmo_errors_total", "Total system alarms triggered")
3. Update the Data Flow
Inside your cloud_thread, right after you extract the temp variable from the sensor data, we will add two lines of code to update the metrics:
```

3. Update the Data Flow
Inside your cloud_thread, right after you extract the temp variable from the sensor data, we will add two lines of code to update the metrics

``
prom_packets.inc()          # Increase the packet counter by 1
prom_temperature.set(temp)  # Update the gauge to the current temperature
``

We will also add prom_errors.inc() inside your deadman's switch logic so that every time the system detects the sensor has gone offline, we track it as an erro

4. Start the Server
Finally, inside your main() function, right before you start the threads, we will add:

``
start_http_server(8000)
``

This tells Python to open port 8000. If anyone visits http://localhost:8000, they will see a plaintext page listing all your metrics, which is exactly what a professional monitoring system expects!

Does this implementation make sense? If you are ready, I will go ahead and apply these changes to requirements.txt and main.py right now!