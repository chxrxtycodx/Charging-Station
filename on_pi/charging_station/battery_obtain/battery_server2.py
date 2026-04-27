import subprocess
import json
import paho.mqtt.client as mqtt
import threading
import time

# -----------------------------
# Config
# -----------------------------
BROKER = "192.168.12.68"
PORT = 1883
THRESHOLD = 25
BATTERY_SCRIPT = "/home/pi/charging_station/battery_obtain/battery_server2.py"
REMIND_INTERVAL = 300  # 5 minutes
PRESENCE_TIMEOUT = 15  # seconds

# -----------------------------
# State
# -----------------------------
batteries = {}
presence = False
reminder_active = False
last_presence_time = 0

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
        payload = json.dumps({"percent": worst_percent, "plugged": False})
    else:
        payload = json.dumps({"percent": 100, "plugged": True})

    client.publish("devices/battery", payload)
    print(f"[LED] Published: {payload}")

# -----------------------------
# Battery Scripts
# -----------------------------
def start_battery_scripts():
    print("[Pi] Starting battery server...")
    subprocess.Popen(["python3", BATTERY_SCRIPT])

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

        # Broadcast start
        client.publish("OSOROC/presence/start", "true")

        start_battery_scripts()
        time.sleep(2)
        announce(build_status_message())
        publish_to_led()
        start_reminders()

    elif not detected and presence:
        presence = False
        reminder_active = False
        print("[Pi] Presence cleared")

        # Broadcast stop
        client.publish("OSOROC/presence/stop", "true")

# -----------------------------
# Presence Timeout Watcher
# -----------------------------
def presence_watcher():
    global presence, last_presence_time
    while True:
        time.sleep(1)
        if presence and (time.time() - last_presence_time > PRESENCE_TIMEOUT):
            print("[Pi] Presence timeout — clearing presence")
            handle_presence(False)

threading.Thread(target=presence_watcher, daemon=True).start()

# -----------------------------
# MQTT client
# -----------------------------
client = mqtt.Client(client_id="pi-controller", protocol=mqtt.MQTTv311)

# -----------------------------
# MQTT Callbacks
# -----------------------------
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with code {rc}")

    client.subscribe("OSOROC/ranger/presence")
    client.subscribe("OSOROC/devices/battery/+")
    client.subscribe("OSOROC/devices/event/+")

def on_message(client, userdata, msg):
    global last_presence_time

    topic = msg.topic
    payload = msg.payload.decode()
    print(f"[MQTT] {topic}: {payload}")

    # ---- Ranger presence ----
    if topic == "OSOROC/ranger/presence":
        try:
            data = json.loads(payload)
            detected = data.get("presence", False)

            if detected:
                last_presence_time = time.time()
                handle_presence(True)

        except:
            pass
        return

    # Extract device name
    device = topic.split("/")[-1]

    # ---- Battery JSON ----
    if "/battery/" in topic:
        try:
            data = json.loads(payload)

            percent = data.get("percent", 100)
            plugged = data.get("plugged", True)
            timestamp = data.get("timestamp", "00:00:00:00:00")

            if device not in batteries:
                batteries[device] = {}

            batteries[device]["percent"] = percent
            batteries[device]["plugged"] = plugged
            batteries[device]["timestamp"] = timestamp

            print(f"[Battery] {device}: {percent}% plugged={plugged} at {timestamp}")
            publish_to_led()

        except json.JSONDecodeError:
            print(f"[Error] Could not parse battery payload: {payload}")

    # ---- Plug/unplug event ----
    elif "/event/" in topic:
        if device not in batteries:
            batteries[device] = {}

        batteries[device]["plugged"] = (payload == "plugged")
        print(f"[Event] {device} plugged={payload == 'plugged'}")
        publish_to_led()

# -----------------------------
# Main
# -----------------------------
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

print("[Pi] Controller running...")
client.loop_forever()
