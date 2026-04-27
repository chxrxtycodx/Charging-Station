import paho.mqtt.client as mqtt
import json, subprocess, time
from rpi_ws281x import PixelStrip, Color
from apscheduler.schedulers.background import BackgroundScheduler

MQTT_BROKER = "localhost"
LED_COUNT = 4
LED_PIN = 18

strip = PixelStrip(LED_COUNT, LED_PIN)
strip.begin()

LED_MAP = {
    "samsung": 0,
    "laptop":  1,
    "airpods": 2,
    "gamepad": 3,
}

device_state = {k: {"battery": 100, "checked_in": False} for k in LED_MAP}

def update_leds():
    colors = {"ok": Color(0,150,0), "warn": Color(255,165,0), "alert": Color(200,0,0), "off": Color(0,0,0)}
    for dev, idx in LED_MAP.items():
        s = device_state[dev]
        if s["checked_in"]:
            strip.setPixelColor(idx, colors["off"])
        elif s["battery"] <= 25:
            strip.setPixelColor(idx, colors["alert"])
        elif s["battery"] <= 50:
            strip.setPixelColor(idx, colors["warn"])
        else:
            strip.setPixelColor(idx, colors["ok"])
    strip.show()

def speak_alert(device_name):
    subprocess.run(["espeak", f"Please charge your {device_name}"])

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = json.loads(msg.payload)
    dev_id = payload.get("device")
    battery = payload.get("battery")
    if dev_id in device_state:
        device_state[dev_id]["battery"] = battery
        if battery <= 25 and not device_state[dev_id]["checked_in"]:
            speak_alert(dev_id)
        update_leds()

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER)
client.subscribe("chargedock/battery")
client.subscribe("chargedock/checkin")
client.loop_forever()
