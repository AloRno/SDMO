import os
import sys
import time
import threading
import logging
from prometheus_client import start_http_server, Counter, Gauge

from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

# Configure basic logging for the main daemon
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("SDMO_Daemon")

# Prometheus Metrics
prom_packets = Counter("sdmo_packets_total", "Total packets processed by the Cloud")
prom_temperature = Gauge("sdmo_temperature_celsius", "Current temperature reading")
prom_errors = Counter("sdmo_errors_total", "Total system alarms triggered")

def device_thread(device, stop_event):
    while not stop_event.is_set():
        raw_data = device.generateData(failure_probability=0.0)
        encrypted_cbc = device.encryptData(raw_data)
        device.sendEncryptedData(encrypted_cbc, corruption_probability=0.0)
        time.sleep(1.5)

def gateway_thread(gateway, device, cloud, stop_event):
    while not stop_event.is_set():
        received = gateway.receiveData(device)
        if received:
            plaintext = gateway.decryptData(received)
            if plaintext:
                reencrypted = gateway.reEncryptData(plaintext)
                gateway.forwardData(cloud, reencrypted)
        time.sleep(0.5)

def cloud_thread(cloud, stop_event):
    alarm_active = False
    while not stop_event.is_set():
        result = cloud.processData()
        if result:  
            temp_str, ts_str = result.split("|")
            temp = float(temp_str)
            
            # Update Prometheus metrics
            prom_packets.inc()
            prom_temperature.set(temp)
            
        # Deadman's switch / Health Check
        time_since = time.time() - cloud.last_healthy_reading_time
        if time_since > 15.0:
            if not alarm_active:
                cloud.check_sensor_health(timeout_seconds=15)
                alarm_active = True
                prom_errors.inc()
                logger.error("Sensor unreachable. Alarm active.")
        else:
            if alarm_active:
                logger.info("Sensor health restored.")
                alarm_active = False
                
        time.sleep(0.5)

def main():
    logger.info("Starting SDMO Pipeline Daemon...")
    
    # Start Prometheus metrics server
    start_http_server(8000)
    logger.info("Prometheus metrics server running on port 8000.")

    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    logger.info("Negotiating session (Hybrid DH + ML-KEM)...")
    gateway.negotiateSession(cloud)
    logger.info("Session negotiated successfully!")
    
    stop_event = threading.Event()
    
    t_device = threading.Thread(target=device_thread, args=(device, stop_event), daemon=True)
    t_gateway = threading.Thread(target=gateway_thread, args=(gateway, device, cloud, stop_event), daemon=True)
    t_cloud = threading.Thread(target=cloud_thread, args=(cloud, stop_event), daemon=True)
    
    t_device.start()
    t_gateway.start()
    t_cloud.start()
    
    logger.info("Pipeline threads started. Running silently in the background...")
    
    try:
        iterations = 0
        while True:
            time.sleep(0.25)
            # If running inside GitHub Actions (CI smoke test), exit gracefully after 10s
            if os.environ.get("CI") == "true":
                iterations += 1
                if iterations >= 40:
                    logger.info("CI smoke test complete. Shutting down.")
                    break
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt. Shutting down.")
    finally:
        stop_event.set()
        t_device.join(timeout=1.0)
        t_gateway.join(timeout=1.0)
        t_cloud.join(timeout=1.0)
        logger.info("Daemon terminated cleanly.")
        
if __name__ == "__main__":
    main()