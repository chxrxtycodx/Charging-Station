#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <map>

// WiFi + MQTT Configuration
const char* ssid = "Charging Wifi";
const char* password = "12355555";
const char* mqtt_server = "10.143.170.254";

WiFiClient espClient;
PubSubClient client(espClient);

// LED Pin (PWM-capable pin)
const int alertLED = 21;

// LED State
bool shouldBeOn = true;
int currentBrightness = 255;

// Dynamic settings from OSOROC/setting
int dimPercentage = 0;          // 0–100
int brightnessPercentage = 100; // 0–100
int lowBatteryThreshold = 25;   // 0–100

// Computed brightness limits
int minBrightness = 0;
int maxBrightness = 255;

// Track all devices and their low-battery status
std::map<String, bool> deviceLowState;

// WiFi Setup
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// Apply new brightness limits
void updateBrightnessBounds() {
  minBrightness = map(dimPercentage, 0, 100, 0, 255);
  maxBrightness = map(brightnessPercentage, 0, 100, 0, 255);

  if (minBrightness > maxBrightness) {
    int t = minBrightness;
    minBrightness = maxBrightness;
    maxBrightness = t;
  }

  Serial.print("Brightness range updated → ");
  Serial.print(minBrightness);
  Serial.print(" to ");
  Serial.println(maxBrightness);
}

// Recompute LED state based on all devices
void recomputeShouldBeOn() {
  for (auto &entry : deviceLowState) {
    if (entry.second == true) {
      shouldBeOn = false;
      return;
    }
  }
  shouldBeOn = true;
}

// MQTT Callback
void callback(char* topic, byte* message, unsigned int length) {
  String payload;
  for (int i = 0; i < length; i++) payload += (char)message[i];

  Serial.print("Message on ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(payload);

  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload)) {
    Serial.println("JSON parse failed!");
    return;
  }

  // Topic for settings
  if (String(topic) == "OSOROC/setting") {
    if (doc.containsKey("dimPercentage")) 
        dimPercentage = doc["dimPercentage"];

    if (doc.containsKey("brightnessPercentage")) 
        brightnessPercentage = doc["brightnessPercentage"];

    if (doc.containsKey("lowBatteryThreshold")) 
        lowBatteryThreshold = doc["lowBatteryThreshold"];

    updateBrightnessBounds();

    // NEW: Apply new threshold to all devices immediately
    recomputeShouldBeOn();

    return;
  }

  // Battery Topic
  String device = doc["device"] | "unknown";
  float percent = doc["percent"];
  bool plugged = doc["plugged"];

  Serial.print("Device: ");
  Serial.println(device);
  Serial.print("Percent: ");
  Serial.println(percent);
  Serial.print("Plugged: ");
  Serial.println(plugged);

  // Determine if this device is in a low-battery state
  bool isLow = (percent < lowBatteryThreshold && plugged == false);

  // Update device state
  deviceLowState[device] = isLow;

  // Recompute global LED state
  recomputeShouldBeOn();
}

// MQTT Reconnect
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32BatteryMonitorJSON")) {
      Serial.println("connected");

      client.subscribe("OSOROC/devices/battery/#");
      client.subscribe("OSOROC/setting");

    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

// Setup
void setup() {
  Serial.begin(115200);

  ledcAttach(alertLED, 5000, 8);
  ledcWrite(alertLED, 255);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  updateBrightnessBounds();
}

// Smooth Transition Function
void smoothTransition() {
  int target = shouldBeOn ? maxBrightness : minBrightness;

  if (currentBrightness == target) return;

  if (currentBrightness < target) currentBrightness++;
  else currentBrightness--;

  ledcWrite(alertLED, currentBrightness);
  delay(5);
}

// Loop
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  smoothTransition();
}
