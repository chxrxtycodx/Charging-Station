import json
import platform
import time
from datetime import datetime
import psutil
import paho.mqtt.client as mqtt
import traceback
import sys

BROKER = "10.143.170.254"
PORT = 1883
DEVICE = platform.node()

PUBLISH_INTERVAL = 10
publishing_enabled = False

def log(msg):
    print(msg)
    sys.stdout.flush()

def get_payload():
    battery = psutil.sensors_battery()
    timestamp = datetime.now().strftime("%m:%d:%H:%M:%S")

    if battery is None:
        return {"device": DEVICE, "timestamp": timestamp}

    return {
        "device": DEVICE,
        "percent": battery.percent,
        "plugged": battery.power_plugged,
        "timestamp": timestamp
    }

def on_message(client, userdata, msg):
    global publishing_enabled
    topic = msg.topic

    if topic == "OSOROC/presence/start":
        publishing_enabled = True
        log("[Laptop] Publishing ENABLED")

    elif topic == "OSOROC/presence/stop":
        publishing_enabled = False
        log("[Laptop] Publishing DISABLED")

def main():
    log("[Laptop] Service started")

    client = mqtt.Client()
    client.on_message = on_message

    while True:
        try:
            client.connect(BROKER, PORT)
            client.subscribe("OSOROC/presence/#")
            client.loop_start()
            break
        except Exception as e:
            log("[Laptop] MQTT connect failed, retrying...")
            log(str(e))
            time.sleep(5)

    log("[Laptop] Waiting for presence commands...")

    while True:
        try:
            if publishing_enabled:
                payload = json.dumps(get_payload())
                topic = f"OSOROC/devices/battery/{DEVICE}"
                client.publish(topic, payload)
                log("[Laptop] Published: " + payload)

            time.sleep(PUBLISH_INTERVAL)

        except Exception as e:
            log("[Laptop] ERROR in main loop:")
            log(traceback.format_exc())
            time.sleep(5)

if __name__ == "__main__":
    main()
