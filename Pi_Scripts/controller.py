import subprocess
import json
import paho.mqtt.client as mqtt
import threading
import time

# -----------------------------
# Config
# -----------------------------
BROKER = "10.143.170.254"
PORT = 1883
THRESHOLD = 25
BATTERY_SCRIPT = "/home/pi/charging_station/battery_obtain/battery_server.py"
REMIND_INTERVAL = 300  # 5 minutes

# -----------------------------
# State
# -----------------------------
batteries = {}
presence = False
reminder_active = False

# -----------------------------
# MQTT client
# -----------------------------
client = mqtt.Client(client_id="pi-controller", protocol=mqtt.MQTTv311)

# -----------------------------
# Audio
# -----------------------------
def announce(text):
    print(f"[espeak] {text}")
    subprocess.run(["espeak", text])

def build_status_message():
    msgs = []
    for device, info in batteries.items():
        percent = info.get("percent", 100)
        plugged = info.get("plugged", True)
        if percent < THRESHOLD and not plugged:
            msgs.append(f"{device} is at {int(percent)} percent")
    return ", ".join(msgs) if msgs else "All devices are charged"

# -----------------------------
# LED Publisher
# -----------------------------
def publish_to_led():
    """Find worst unplugged device and publish to LED ESP32"""
    if not batteries:
        return

    worst_device = None
    worst_percent = 100

    for device, info in batteries.items():
        percent = info.get("percent", 100)
        plugged = info.get("plugged", True)
        if not plugged and percent < worst_percent:
            worst_percent = percent
            worst_device = device

    if worst_device:
        payload = json.dumps({
            "percent": worst_percent,
            "plugged": False
        })
    else:
        payload = json.dumps({
            "percent": 100,
            "plugged": True
        })

    client.publish("OSOROC/devices/battery", payload)
    print(f"[LED] Published: {payload}")

# -----------------------------
# Battery Scripts
# -----------------------------
def start_battery_scripts():
    print("[Pi] Starting battery server...")
    subprocess.Popen(["python3", BATTERY_SCRIPT])
    # add partner scripts here once paths are known:
    # subprocess.Popen(["python3", "/path/to/partner_script.py"])

# -----------------------------
# Reminders
# -----------------------------
def start_reminders():
    global reminder_active
    reminder_active = True

    def remind():
        while presence and reminder_active:
            time.sleep(REMIND_INTERVAL)
            low_devices = [
                d for d, info in batteries.items()
                if info.get("percent", 100) < THRESHOLD and not info.get("plugged", True)
            ]
            if low_devices:
                announce(build_status_message())
                publish_to_led()

    threading.Thread(target=remind, daemon=True).start()
    print("[Pi] Reminders started")

# -----------------------------
# Presence Handler
# -----------------------------
def handle_presence(detected: bool):
    global presence, reminder_active

    if detected and not presence:
        presence = True
        print("[Pi] Presence detected")
        start_battery_scripts()
        time.sleep(2)
        announce(build_status_message())
        publish_to_led()
        start_reminders()

    elif not detected and presence:
        presence = False
        reminder_active = False
        print("[Pi] Presence cleared")

# -----------------------------
# MQTT Callbacks
# -----------------------------
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}")
    client.subscribe("OSOROC/ranger/presence")
    client.subscribe("OSOROC/devices/+/battery")
    client.subscribe("OSOROC/devices/+/event")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"[MQTT] {topic}: {payload}")

    # ---- Ranger presence ----
    if topic == "OSOROC/ranger/presence":
        detected = payload.lower() == "true"
        handle_presence(detected)

    # ---- Battery level ----
    elif topic.startswith("OSOROC/devices/") and topic.endswith("/battery"):
        try:
            data = json.loads(payload)
            device = data.get("device", topic.split("/")[2])
            percent = data.get("percent", 100)
            plugged = data.get("plugged", data.get("charging", True))

            if device not in batteries:
                batteries[device] = {}

            batteries[device]["percent"] = percent
            batteries[device]["plugged"] = plugged

            print(f"[Battery] {device}: {percent}% plugged={plugged}")
            publish_to_led()

        except json.JSONDecodeError:
            print(f"[Error] Could not parse battery payload: {payload}")

    # ---- Plugged/unplugged event ----
    elif topic.startswith("OSOROC/devices/") and topic.endswith("/event"):
        device = topic.split("/")[2]
        if device not in batteries:
            batteries[device] = {}
        batteries[device]["plugged"] = (payload == "plugged")
        publish_to_led()

# -----------------------------
# Main
# -----------------------------
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

print("[Pi] Controller running...")
client.loop_forever()
