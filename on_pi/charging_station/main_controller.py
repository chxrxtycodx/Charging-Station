#!/usr/bin/env python3
import json
import paho.mqtt.client as mqtt
import threading
import time
import subprocess
import queue
import traceback

# -----------------------------
# Config
# -----------------------------
BROKER = "10.143.170.254"
PORT = 1883
THRESHOLD = 25
REMIND_INTERVAL = 300  # 5 minutes
PRESENCE_TIMEOUT = 15  # seconds

# -----------------------------
# State
# -----------------------------
batteries = {}
presence = False
reminder_active = False
last_presence_time = 0

# Thread-safe task queue
task_queue = queue.Queue()

# -----------------------------
# MQTT client (created early so functions can reference it)
# -----------------------------
client = mqtt.Client(client_id="pi-controller", protocol=mqtt.MQTTv311)

# -----------------------------
# Utility logging
# -----------------------------
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        # Avoid any print-related crashes
        pass

def log_exception(prefix="Exception"):
    safe_print(f"[Error] {prefix}:")
    try:
        traceback.print_exc()
    except Exception:
        safe_print("[Error] (traceback unavailable)")

# -----------------------------
# Audio
# -----------------------------
def announce(text):
    safe_print(f"[espeak] {text}")
    try:
        # Do not raise on failure; capture output to avoid blocking
        subprocess.run(["espeak", text], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        safe_print("[Error] espeak failed:", e)

def build_status_message():
    msgs = []
    try:
        for device, info in batteries.items():
            percent = info.get("percent", 100)
            plugged = info.get("plugged", True)

            try:
                percent = int(percent)
            except (ValueError, TypeError):
                percent = 100

            if isinstance(plugged, str):
                plugged = plugged.strip().lower() in ["true", "1", "yes", "plugged", "charging"]
            else:
                plugged = bool(plugged)

            if percent < THRESHOLD and not plugged:
                msgs.append(f"{device} is at {int(percent)} percent")
    except Exception:
        log_exception("build_status_message crashed")

    return ", ".join(msgs) if msgs else "All devices are charged"

# -----------------------------
# LED Publisher
# -----------------------------
def publish_to_led():
    try:
        if not batteries:
            return

        worst_device = None
        worst_percent = 100

        for device, info in batteries.items():
            percent = info.get("percent", 100)
            plugged = info.get("plugged", True)

            try:
                percent = int(percent)
            except (ValueError, TypeError):
                percent = 100

            if isinstance(plugged, str):
                plugged = plugged.strip().lower() in ["true", "1", "yes", "plugged", "charging"]
            else:
                plugged = bool(plugged)

            if not plugged and percent < worst_percent:
                worst_percent = percent
                worst_device = device

        if worst_device:
            payload = json.dumps({"percent": worst_percent, "plugged": False})
        else:
            payload = json.dumps({"percent": 100, "plugged": True})

        try:
            client.publish("devices/battery", payload)
            safe_print(f"[LED] Published: {payload}")
        except Exception as e:
            safe_print("[Error] LED publish failed:", e)
    except Exception:
        log_exception("publish_to_led crashed")

# -----------------------------
# Reminders
# -----------------------------
def start_reminders():
    global reminder_active
    reminder_active = True

    def remind():
        try:
            while True:
                # Only run reminders while presence is True and reminder_active is True
                if not (presence and reminder_active):
                    break
                time.sleep(REMIND_INTERVAL)
                try:
                    low_devices = []
                    for d, info in batteries.items():
                        try:
                            pct = int(info.get("percent", 100))
                        except (ValueError, TypeError):
                            pct = 100

                        plugged_val = info.get("plugged", True)
                        if isinstance(plugged_val, str):
                            plugged = plugged_val.strip().lower() in ["true", "1", "yes", "plugged", "charging"]
                        else:
                            plugged = bool(plugged_val)

                        if pct < THRESHOLD and not plugged:
                            low_devices.append(d)

                    if low_devices:
                        announce(build_status_message())
                        publish_to_led()
                except Exception:
                    log_exception("remind loop iteration crashed")
        except Exception:
            log_exception("Reminder thread crashed")

    threading.Thread(target=remind, daemon=True).start()
    safe_print("[Pi] Reminders started")

# -----------------------------
# 20-Minute Delayed Stop
# -----------------------------
def schedule_presence_stop():
    def delayed_stop():
        try:
            time.sleep(20 * 60)  # 20 minutes
            # Put the task on the queue so handle_presence runs in dispatcher
            if presence:
                task_queue.put(("presence", False))
        except Exception:
            log_exception("Delayed stop crashed")

    threading.Thread(target=delayed_stop, daemon=True).start()

# -----------------------------
# Presence Handler (ONLY RUNS IN DISPATCHER THREAD)
# -----------------------------
def handle_presence(detected: bool):
    global presence, reminder_active
    try:
        if detected and not presence:
            presence = True
            safe_print("[Pi] Presence detected")

            try:
                client.publish("OSOROC/presence/start", "true")
            except Exception as e:
                safe_print("[Error] publish presence/start failed:", e)

            announce(build_status_message())
            publish_to_led()
            start_reminders()

            schedule_presence_stop()

        elif not detected and presence:
            presence = False
            reminder_active = False
            safe_print("[Pi] Presence cleared")

            try:
                client.publish("OSOROC/presence/stop", "true")
            except Exception as e:
                safe_print("[Error] publish presence/stop failed:", e)
    except Exception:
        log_exception("handle_presence crashed")

# -----------------------------
# Presence Timeout Watcher
# -----------------------------
def presence_watcher():
    global presence, last_presence_time
    while True:
        try:
            time.sleep(1)
            if presence and (time.time() - last_presence_time > PRESENCE_TIMEOUT):
                safe_print("[Pi] Presence timeout — scheduling presence clear")
                task_queue.put(("presence", False))
        except Exception:
            log_exception("Presence watcher crashed")
            # Sleep briefly to avoid tight crash loop
            time.sleep(1)

threading.Thread(target=presence_watcher, daemon=True).start()

# -----------------------------
# Task Dispatcher (Thread-safe)
# -----------------------------
def task_dispatcher():
    while True:
        try:
            task, value = task_queue.get()
            if task == "presence":
                handle_presence(value)
        except Exception:
            log_exception("Task dispatcher crashed")
            # Continue processing further tasks

threading.Thread(target=task_dispatcher, daemon=True).start()

# -----------------------------
# MQTT Callbacks
# -----------------------------
def on_connect(client_obj, userdata, flags, rc):
    # Silence normal connection logs; only print on error
    if rc != 0:
        safe_print(f"[MQTT] Connection error: {rc}")

    try:
        client_obj.subscribe("OSOROC/ranger/presence")
        client_obj.subscribe("OSOROC/devices/battery/+")
        client_obj.subscribe("OSOROC/devices/event/+")
    except Exception:
        log_exception("on_connect subscribe failed")

def on_message(client_obj, userdata, msg):
    global last_presence_time
    try:
        topic = msg.topic
        try:
            payload = msg.payload.decode()
        except Exception:
            payload = msg.payload if isinstance(msg.payload, str) else msg.payload.decode(errors="ignore")
        safe_print(f"[MQTT] {topic}: {payload}")

        # ---- Ranger presence ----
        if topic == "OSOROC/ranger/presence":
            try:
                data = json.loads(payload)
                detected = data.get("presence", False)

                if detected:
                    last_presence_time = time.time()
                    task_queue.put(("presence", True))
            except Exception:
                # If payload isn't JSON, ignore
                log_exception("Failed to parse ranger presence payload")
            return

        # ---- Battery JSON ----
        if "/battery/" in topic:
            try:
                data = json.loads(payload)

                device = data.get("device", topic.split("/")[-1])
                percent = data.get("percent", 100)
                plugged = data.get("plugged", True)
                timestamp = data.get("timestamp", "00:00:00:00:00")

                try:
                    percent = int(percent)
                except (ValueError, TypeError):
                    percent = 100

                if isinstance(plugged, str):
                    plugged = plugged.strip().lower() in ["true", "1", "yes", "plugged", "charging"]
                else:
                    plugged = bool(plugged)

                if device not in batteries:
                    batteries[device] = {}

                batteries[device]["percent"] = percent
                batteries[device]["plugged"] = plugged
                batteries[device]["timestamp"] = timestamp

                safe_print(f"[Battery] {device}: {percent}% plugged={plugged} at {timestamp}")
                publish_to_led()

            except json.JSONDecodeError:
                safe_print(f"[Error] Could not parse battery payload: {payload}")
            except Exception:
                log_exception("Error handling battery message")

        # ---- Plug/unplug event ----
        elif "/event/" in topic:
            try:
                device = topic.split("/")[-1]

                if device not in batteries:
                    batteries[device] = {}

                batteries[device]["plugged"] = (payload == "plugged")
                safe_print(f"[Event] {device} plugged={payload == 'plugged'}")
                publish_to_led()
            except Exception:
                log_exception("Error handling event message")

    except Exception:
        log_exception("on_message crashed")

# -----------------------------
# Main
# -----------------------------
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT)
except Exception:
    log_exception("MQTT connect failed")

safe_print("[Pi] Controller running...")
try:
    client.loop_forever()
except KeyboardInterrupt:
    safe_print("[Pi] Shutting down (KeyboardInterrupt)")
except Exception:
    log_exception("MQTT loop crashed")
