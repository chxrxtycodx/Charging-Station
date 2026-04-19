import time
import json
import platform
from datetime import datetime

import psutil
import paho.mqtt.client as mqtt

# -----------------------------
# MQTT CONFIG
# -----------------------------
BROKER = "10.143.170.254"
PORT = 1883
TOPIC = "devices/laptop/battery"
CLIENT_ID = f"laptop-battery-{platform.node()}"

# Optional if your broker requires login
USERNAME = None
PASSWORD = None

# -----------------------------
# DEVICE CONFIG
# -----------------------------
DEVICE_NAME = platform.node()
PUBLISH_INTERVAL = 60  # seconds

# -----------------------------
# MQTT SETUP
# -----------------------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)

if USERNAME and PASSWORD:
    client.username_pw_set(USERNAME, PASSWORD)

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to MQTT broker with code: {reason_code}")

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print(f"Disconnected from MQTT broker with code: {reason_code}")

client.on_connect = on_connect
client.on_disconnect = on_disconnect

# -----------------------------
# BATTERY READ FUNCTION
# -----------------------------
def get_battery_payload():
    battery = psutil.sensors_battery()

    if battery is None:
        return {
            "device_name": DEVICE_NAME,
            "battery_available": False,
            "timestamp": datetime.now().isoformat()
        }

    return {
        "device_name": DEVICE_NAME,
        "battery_available": True,
        "percent": battery.percent,
        "charging": battery.power_plugged,
        "seconds_left": battery.secsleft,
        "timestamp": datetime.now().isoformat()
    }

# -----------------------------
# MAIN LOOP
# -----------------------------
def main():
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            payload = get_battery_payload()
            payload_str = json.dumps(payload)

            result = client.publish(TOPIC, payload_str)
            print("Published:", payload_str, "| MQTT rc =", result.rc)

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("Stopping publisher...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()