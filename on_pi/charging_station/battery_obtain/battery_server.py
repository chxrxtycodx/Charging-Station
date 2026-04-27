from flask import Flask, request
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)

BROKER = "10.143.170.254"
PORT = 1883

devices = {}

def mqtt_publish(device, percent, plugged, timestamp):
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)

    topic = f"OSOROC/devices/battery/{device.lower()}"
    payload = {
        "device": device,
        "percent": percent,
        "plugged": plugged,
        "timestamp": timestamp
    }

    result = client.publish(topic, json.dumps(payload))
    client.loop(1)

    print("MQTT topic:", topic)
    print("MQTT payload:", json.dumps(payload))
    print("MQTT publish rc:", result.rc)

    client.disconnect()

@app.route('/battery', methods=['POST'])
def battery():
    data = request.get_json(silent=True)

    print("HTTP /battery request received")
    print("HTTP JSON body:", data)

    if not data:
        return {"status": "error", "message": "No JSON received"}, 400

    device = data.get('device', 'unknown')
    percent = data.get('percent', -1)
    plugged = data.get('plugged', False)
    timestamp = data.get('timestamp', 'unknown')

    devices[device] = {
        "percent": percent,
        "plugged": plugged,
        "timestamp": timestamp
    }

    print(f"{device}: {percent}% — plugged={plugged} — {timestamp}")
    print("Publishing to MQTT now...")
    mqtt_publish(device, percent, plugged, timestamp)

    return {"status": "ok"}, 200

@app.route('/', methods=['GET'])
def dashboard():
    html = "<h1>ChargeSense</h1>"
    for device, info in devices.items():
        html += (
            f"<p>{device}: {info['percent']}% — "
            f"plugged={info['plugged']} — {info['timestamp']}</p>"
        )
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
