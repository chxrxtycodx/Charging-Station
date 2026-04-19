import json
import platform
from datetime import datetime

import psutil
import paho.mqtt.client as mqtt

# MQTT CONFIG
BROKER = "10.143.170.254"
PORT = 1883
TOPIC = "OSORO/devices/battery/laptop"
CLIENT_ID = f"laptop-battery-{platform.node()}"

# Optional if your broker requires login
USERNAME = None
PASSWORD = None

# DEVICE CONFIG
DEVICE_NAME = platform.node()

# MQTT SETUP
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

    # Format: MM:DD:HH:mm:ss
    current_time = datetime.now().strftime("%m:%d:%H:%M:%S")

    if battery is None:
        return {
            "device_name": DEVICE_NAME,
            "timestamp": current_time
        }

    return {
        "device_name": DEVICE_NAME,
        "percent": battery.percent,
        "plugged": battery.power_plugged,
        "timestamp": current_time
    }

# MAIN EXECUTION
def main():
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    # Prepare and publish payload
    payload = get_battery_payload()
    payload_str = json.dumps(payload)
    
    # client.publish returns an MQTTMessageInfo object
    info = client.publish(TOPIC, payload_str)
    
    # Wait for the message to be sent to the broker
    info.wait_for_publish()
    
    print("Published:", payload_str)

    # Clean up
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    main()
