import time
import psutil
import paho.mqtt.client as mqtt

BROKER = "test.mosquitto.org"
TOPIC = "laptop/battery"
CLIENT_ID = "LaptopBatteryPublisher"

def get_battery_info():
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    return {
        "percent": battery.percent,
        "plugged": battery.power_plugged
    }

def main():
    client = mqtt.Client(client_id=CLIENT_ID)
    client.connect(BROKER, 1883, 60)
    client.loop_start()

    while True:
        info = get_battery_info()
        if info:
            payload = f"{info['percent']}#{info['plugged']}"
            client.publish(TOPIC, payload)
            print("Published:", payload)
        else:
            print("No battery detected")
        time.sleep(10)

if __name__ == "__main__":
    main()
