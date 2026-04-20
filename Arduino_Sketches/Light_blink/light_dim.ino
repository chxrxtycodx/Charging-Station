#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// -----------------------------
// WiFi + MQTT Configuration
// -----------------------------
const char* ssid = "Charging Wifi";
const char* password = "12355555";
const char* mqtt_server = "10.143.170.254";

WiFiClient espClient;
PubSubClient client(espClient);

// -----------------------------
// LED Pin (PWM-capable pin)
// -----------------------------
const int alertLED = 21;

// -----------------------------
// LED State
// -----------------------------
bool shouldBeOn = true;   // desired LED state
int currentBrightness = 255;  // current PWM value (0–255)

// -----------------------------
// WiFi Setup
// -----------------------------
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

// -----------------------------
// MQTT Callback
// -----------------------------
void callback(char* topic, byte* message, unsigned int length) {
  String payload;
  for (int i = 0; i < length; i++) {
    payload += (char)message[i];
  }

  Serial.print("Message on ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(payload);

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload);

  if (error) {
    Serial.println("JSON parse failed!");
    return;
  }

  float percent = doc["percent"];
  bool plugged = doc["plugged"];

  Serial.print("Parsed percent: ");
  Serial.println(percent);
  Serial.print("Parsed plugged: ");
  Serial.println(plugged);

  // Simple logic:
  // LED OFF if low battery AND not plugged
  // LED ON otherwise
  if (percent < 25 && plugged == false) {
    shouldBeOn = false;
  } else {
    shouldBeOn = true;
  }
}

// -----------------------------
// MQTT Reconnect
// -----------------------------
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32BatteryMonitorJSON")) {
      Serial.println("connected");
      client.subscribe("OSOROC/devices/battery/#");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds");
      delay(5000);
    }
  }
}

// -----------------------------
// Setup
// -----------------------------
void setup() {
  Serial.begin(115200);

  // Attach LED to PWM
  ledcAttach(alertLED, 5000, 8);  // pin, frequency, resolution

  // Start LED ON
  ledcWrite(alertLED, 255);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

// -----------------------------
// Smooth Transition Function
// -----------------------------
void smoothTransition() {
  int target = shouldBeOn ? 255 : 0;

  if (currentBrightness == target) return;

  if (currentBrightness < target) currentBrightness++;
  else currentBrightness--;

  ledcWrite(alertLED, currentBrightness);
  delay(5);  // controls speed of transition
}

// -----------------------------
// Loop
// -----------------------------
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Smoothly move toward ON or OFF
  smoothTransition();
}
