#!/usr/bin/env python3
"""
espeak TTS test script for Raspberry Pi
Tests various espeak features for the ChargeSense voice notification system
"""

import subprocess
import time

def speak(text, voice="en", speed=150, pitch=50, volume=100):
    """Wrapper around espeak CLI"""
    cmd = [
        "espeak",
        "-v", voice,
        "-s", str(speed),    # speed: words per minute (default 160)
        "-p", str(pitch),    # pitch: 0-99
        "-a", str(volume),   # amplitude/volume: 0-200
        text
    ]
    subprocess.run(cmd)

def speak_async(text, voice="en", speed=150, pitch=50, volume=100):
    """Non-blocking speak — returns immediately"""
    cmd = ["espeak", "-v", voice, "-s", str(speed), "-p", str(pitch), "-a", str(volume), text]
    return subprocess.Popen(cmd)

# --- Tests ---

print("Test 1: Basic speech")
speak("Hello! espeak is working on your Raspberry Pi.")
time.sleep(0.5)

print("Test 2: ChargeSense notification messages")
messages = [
    "Your phone battery is at 20 percent. Please charge it.",
    "Warning! Laptop battery is critically low at 10 percent.",
    "All devices are fully charged. Good job!",
    "iPhone has been charging for 3 hours and is now at 95 percent.",
]
for msg in messages:
    print(f"  Speaking: {msg}")
    speak(msg, speed=150)
    time.sleep(0.3)

print("Test 3: Different voices")
voices = [("en", "English"), ("en-us", "US English"), ("en-gb", "British English")]
for voice_code, voice_name in voices:
    print(f"  Voice: {voice_name}")
    speak(f"This is the {voice_name} voice.", voice=voice_code)
    time.sleep(0.3)

print("Test 4: Urgency levels (speed + pitch variation)")
speak("Reminder: your device needs charging.",         speed=130, pitch=45)  # calm
speak("Alert: battery is getting low.",                speed=155, pitch=55)  # moderate
speak("Warning! Battery critically low, charge now!", speed=175, pitch=70)  # urgent

print("Test 5: Non-blocking (async) speech")
proc = speak_async("This plays while Python keeps running.")
print("  (doing other work while speaking...)")
time.sleep(1)
proc.wait()

print("\nAll tests complete!")
