#include <time.h>
#include <WiFi.h>
#include <PubSubClient.h>

// -----------------------------
// WiFi + MQTT
// -----------------------------
const char* ssid = "Charging Wifi";
const char* password = "12355555";
const char* mqtt_server = "10.143.170.254";

WiFiClient espClient;
PubSubClient client(espClient);

// -----------------------------
// HC-SR04 Pins
// -----------------------------
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;

// -----------------------------
// Detection Config
// -----------------------------
const int DETECTION_DISTANCE = 50;              // cm
const int REQUIRED_DETECTIONS = 1;             // third time
const unsigned long DETECTION_WINDOW = 30;     // ms

// -----------------------------
// State
// -----------------------------
int detectCount = 0;
unsigned long firstDetectionTime = 0;
bool publishedTrue = false;

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
  configTime(0, 0, "pool.ntp.org");
  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// -----------------------------
// MQTT Reconnect
// -----------------------------
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    if (client.connect("ESP32Ranger")) {
      Serial.println("connected");
    } else {
      Serial.print("failed rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5s");
      delay(5000);
    }
  }
}

// -----------------------------
// Get Distance in cm
// -----------------------------
long getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  
  return duration * 0.034 / 2;
}

// -----------------------------
// Publish Presence True
// -----------------------------
void publishPresenceTrue_0() {
  if (client.publish("OSOROC/ranger/presence", "true")) {
    Serial.println("[Ranger] Published true to OSOROC/ranger/presence");
  } else {
    Serial.println("[Ranger] Publish failed");
  }
}

void publishPresenceTrue() {
  time_t now = time(nullptr);  // real Unix timestamp (seconds)

  String payload = "{";
  payload += "\"presence\": true, ";
  payload += "\"timestamp\": ";
  payload += String((long)now);
  payload += "}";

  client.publish("OSOROC/ranger/presence", payload.c_str());

  Serial.println(payload);
}

// -----------------------------
// Setup
// -----------------------------
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

// -----------------------------
// Loop
// -----------------------------
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  long distance = getDistance();
  delay(1000);
  unsigned long now = millis();

  Serial.println(distance);
  // if (distance < 50){
  //   Serial.print("[Ranger] Distance: ");
  //   Serial.print(distance);
  //   Serial.println(" cm");
  // }
  
  if (distance < DETECTION_DISTANCE) {
    // start a new 20 ms window if this is the first detection
    if (detectCount == 0) {
      detectCount = 1;
      firstDetectionTime = now;
    } else {
      // only count if still inside the same 20 ms window
      if (now - firstDetectionTime <= DETECTION_WINDOW) {
        detectCount++;
      } else {
        // old window expired, restart count
        detectCount = 1;
        firstDetectionTime = now;
      }
    }

    Serial.print("Confirmation: ");
    Serial.println(detectCount);

    // if this is the third detection inside the window, publish true
    if (detectCount >= REQUIRED_DETECTIONS && !publishedTrue) {
      publishPresenceTrue();
      publishedTrue = true;
    }
  } else {
    // object no longer detected, reset logic
    detectCount = 0;
    firstDetectionTime = 0;
    publishedTrue = false;
  }
}