import time
import psutil
import json
import paho.mqtt.client as mqtt
from datetime import datetime


BROKER = "test.mosquitto.org"
TOPIC = "devices/battery"
CLIENT_ID = "LaptopBatteryPublisher"
DEVICE_NAME = "Laptop"


def get_battery_info():
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    return {
        "percent": battery.percent,
        "plugged": battery.power_plugged
    }


def main():
    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311
    )


    client.connect(BROKER, 1883, 60)
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


            json_payload = json.dumps(payload)


            client.publish(TOPIC, json_payload)
            print("Published:", json_payload)


        else:
            print("No battery detected")


        time.sleep(10)


if __name__ == "__main__":
    main()
