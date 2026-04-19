import time
import json
import platform
import threading
import psutil
import paho.mqtt.client as mqtt
from datetime import datetime
from flask import Flask, request, jsonify

# -----------------------------
# MQTT CONFIG
# -----------------------------
BROKER = "10.143.170.254"
PORT = 1883
CLIENT_ID = f"laptop-battery-{platform.node()}"
USERNAME = None
PASSWORD = None

# -----------------------------
# DEVICE CONFIG
# -----------------------------
DEVICE_NAME = "laptop"
PUBLISH_INTERVAL = 60
USERNAME_PREFIX = "OSOROC"  # default, can be updated via app

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)

@app.route('/set_user', methods=['POST'])
def set_user():
    global USERNAME_PREFIX
    data = request.json
    if not data or "username" not in data:
        return jsonify({"status": "error", "message": "username required"}), 400
    USERNAME_PREFIX = data["username"]
    print(f"[Flask] Username updated to: {USERNAME_PREFIX}")
    return jsonify({"status": "ok", "username": USERNAME_PREFIX})

@app.route('/status', methods=['GET'])
def status():
    info = get_battery_info()
    return jsonify({
        "username": USERNAME_PREFIX,
        "topic": f"{USERNAME_PREFIX}/devices/laptop/battery",
        "battery": info
    })

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
# MQTT LOOP
# -----------------------------
def mqtt_loop():
    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311
    )

    if USERNAME and PASSWORD:
        client.username_pw_set(USERNAME, PASSWORD)

    def on_connect(client, userdata, flags, rc):
        print(f"[MQTT] Connected with code: {rc}")

    def on_disconnect(client, userdata, rc):
        print(f"[MQTT] Disconnected with code: {rc}")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    while True:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start()

            while True:
                info = get_battery_info()
                topic = f"{USERNAME_PREFIX}/devices/laptop/battery"

                if info:
                    timestamp = datetime.now().strftime("%m:%d:%H:%M:%S")
                    payload = {
                        "device": DEVICE_NAME,
                        "percent": info["percent"],
                        "plugged": info["plugged"],
                        "timestamp": timestamp
                    }
                    client.publish(topic, json.dumps(payload))
                    print(f"[MQTT] Published to {topic}:", json.dumps(payload))
                else:
                    print("[MQTT] No battery detected")

                time.sleep(PUBLISH_INTERVAL)

        except Exception as e:
            print(f"[MQTT] Error: {e}, retrying in 5s...")
            client.loop_stop()
            time.sleep(5)

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    # Run MQTT in background thread
    mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
    mqtt_thread.start()

    # Run Flask on main thread
    print("[Flask] Starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000)