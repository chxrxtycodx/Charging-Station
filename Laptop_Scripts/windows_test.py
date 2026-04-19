import time
import json
import platform
import paho.mqtt.client as mqtt
from datetime import datetime
import psutil

# -----------------------------
# MQTT CONFIG
# -----------------------------
BROKER = "10.143.170.254"
PORT = 1883
TOPIC = "OSOROC/devices/laptop/battery"
CLIENT_ID = f"laptop-battery-{platform.node()}"

USERNAME = None
PASSWORD = None

# -----------------------------
# DEVICE CONFIG
# -----------------------------
DEVICE_NAME = "laptop"
PUBLISH_INTERVAL = 10

# -----------------------------
# BATTERY READ FUNCTION
# -----------------------------
def get_battery_info():
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    return {
        "percent": battery.percent,
        "plugged": battery.power_plugged
    }

# -----------------------------
# MAIN LOOP
# -----------------------------
def main():
    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311
    )

    if USERNAME and PASSWORD:
        client.username_pw_set(USERNAME, PASSWORD)

    def on_connect(client, userdata, flags, rc):
        print(f"Connected to MQTT broker with code: {rc}")

    def on_disconnect(client, userdata, rc):
        print(f"Disconnected from MQTT broker with code: {rc}")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    while True:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start()

            while True:
                info = get_battery_info()
                if info:
                    timestamp = datetime.now().strftime("%m:%d:%H:%M:%S")
                    payload = {
                        "device": DEVICE_NAME,
                        "percent": info["percent"],
                        "plugged": info["plugged"],
                        "timestamp": timestamp
                    }
                    client.publish(TOPIC, json.dumps(payload))
                    print("Published:", json.dumps(payload))
                else:
                    print("No battery detected")

                time.sleep(PUBLISH_INTERVAL)

        except Exception as e:
            print(f"Error: {e}, retrying in 5s...")
            client.loop_stop()
            time.sleep(5)

if __name__ == "__main__":
    main()