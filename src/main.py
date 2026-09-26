import sys
import builtins
import time
from datetime import datetime
import threading
import collections
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
import plotext as plt

from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

# Globals for UI
received_data_log = collections.deque(maxlen=20)
temperature_history = collections.deque(maxlen=60)
stats = {"min": None, "max": None, "count": 0, "sum": 0.0}

console = Console()

# We patch builtins.print so that prints from other threads 
# don't mess up the TUI, but instead go to our live log buffer.
def ui_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    if msg.strip():
        received_data_log.append(msg)

builtins.print = ui_print


def device_thread(device, stop_event):
    while not stop_event.is_set():
        raw_data = device.generateData(failure_probability=0.0)
        encrypted_cbc = device.encryptData(raw_data)
        device.sendEncryptedData(encrypted_cbc, corruption_probability=0.0)
        # Sleep enough to see the UI update pleasantly
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

alarm_active = False

def cloud_thread(cloud, stop_event):
    global alarm_active
    while not stop_event.is_set():
        result = cloud.processData()
        if result:  
            temp_str, ts_str = result.split("|")
            temp = float(temp_str)
            
            # Update stats
            stats["count"] += 1
            stats["sum"] += temp
            if stats["min"] is None or temp < stats["min"]:
                stats["min"] = temp
            if stats["max"] is None or temp > stats["max"]:
                stats["max"] = temp
                
            temperature_history.append(temp)
            ts_int = int(ts_str)
            formatted_ts = datetime.fromtimestamp(ts_int).strftime("%d.%m.%Y | %H:%M:%S")
            received_data_log.append(f"Cloud Processed: temp={temp}C, {formatted_ts}")
            
        # Deadman's switch / Health Check
        # We check every loop, but only trigger the alarm message once per failure incident
        time_since = time.time() - cloud.last_healthy_reading_time
        if time_since > 15.0:  # 15 seconds without healthy data triggers alarm
            if not alarm_active:
                cloud.check_sensor_health(timeout_seconds=15)
                alarm_active = True
        else:
            if alarm_active:
                ui_print("[CloudService] [SUCCESS] Sensor health restored.")
                alarm_active = False
                
        time.sleep(0.5)

def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1)
    )
    layout["main"].split_column(
        Layout(name="graph", ratio=3),
        Layout(name="bottom", ratio=2),
    )
    layout["bottom"].split_row(
        Layout(name="log", ratio=2),
        Layout(name="stats", ratio=1),
    )
    return layout

def update_ui(layout, cloud):
    # Header responds to alarm state
    time_since = time.time() - cloud.last_healthy_reading_time
    if time_since > 15.0:
        header_text = Text("SDMO — Full Pipeline Demo [CRITICAL ALARM: SENSOR UNREACHABLE]", justify="center", style="bold white on red blink")
        border_color = "red"
    else:
        header_text = Text("SDMO — Full Pipeline Demo (TUI)", justify="center", style="bold cyan")
        border_color = "cyan"
        
    layout["header"].update(Panel(header_text))
    
    # Calculate approximate size for the plot
    width = console.width - 4
    height = ((console.height - 3) * 3 // 5) - 2
    if width < 20: width = 20
    if height < 5: height = 5
    
    # Graph using plotext
    plt.clf()
    plt.plotsize(width, height)
    plt.title("Live Temperature Data (°C)")
    plt.theme("dark")
    if temperature_history:
        plt.plot(list(temperature_history), marker="braille", color=border_color)
    else:
        plt.plot([0], marker="braille")
    
    # Build plot and pass ANSI directly to rich
    graph_str = plt.build()
    layout["graph"].update(Panel(Text.from_ansi(graph_str), title="Temperature Graph", border_style=border_color))
    
    # Log
    log_text = Text("\n".join(received_data_log), style="green")
    layout["log"].update(Panel(log_text, title="Live Incoming Data (Cloud Buffer)", border_style="green"))
    
    # Stats
    table = Table(show_header=False, expand=True)
    table.add_column("Stat", style="yellow", justify="right")
    table.add_column("Value", style="bold white", justify="left")
    if stats["count"] > 0:
        avg = stats["sum"] / stats["count"]
        table.add_row("Total Packets", str(stats["count"]))
        table.add_row("Average", f"{avg:.2f} °C")
        table.add_row("Maximum", f"{stats['max']:.2f} °C")
        table.add_row("Minimum", f"{stats['min']:.2f} °C")
    else:
        table.add_row("Waiting for data...", "")
    layout["stats"].update(Panel(table, title="Statistics", border_style="yellow"))


def main():
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    ui_print("Negotiating session (Hybrid DH + ML-KEM)...")
    gateway.negotiateSession(cloud)
    ui_print("Session negotiated successfully!")
    
    stop_event = threading.Event()
    
    t_device = threading.Thread(target=device_thread, args=(device, stop_event), daemon=True)
    t_gateway = threading.Thread(target=gateway_thread, args=(gateway, device, cloud, stop_event), daemon=True)
    t_cloud = threading.Thread(target=cloud_thread, args=(cloud, stop_event), daemon=True)
    
    t_device.start()
    t_gateway.start()
    t_cloud.start()
    
    layout = make_layout()
    
    try:
        # Refresh 4 times a second
        with Live(layout, console=console, refresh_per_second=4, screen=True):
            while True:
                update_ui(layout, cloud)
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        
if __name__ == "__main__":
    main()