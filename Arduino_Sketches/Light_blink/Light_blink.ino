// ArduinoIDE code for ESP32 to light up LED
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>


// -----------------------------
// WiFi + MQTT Configuration
// -----------------------------
const char* ssid = "Charging Wifi";
const char* password = "12355555";
const char* mqtt_server = "test.mosquitto.org";



WiFiClient espClient;
PubSubClient client(espClient);

/ -----------------------------
// PWM + Brightness State
// -----------------------------
const int pwmChannel = 0;
const int pwmFreq = 5000;
const int pwmResolution = 8;

int currentBrightness = 0;  // tracks previous brightness

// -----------------------------
// LED Pin
// -----------------------------
const int alertLED = 21;


// -----------------------------
// Track alert state
// -----------------------------
bool alertActive = false;

//==============================SETUP FUNCTIONS========================================
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

//=================================MAIN FUNCTIONS======================================
int dim_light(int previousBrightness, int changeAmount) {
  int newBrightness = previousBrightness - changeAmount;

  if (newBrightness < 0) {
    newBrightness = 0;
    //*****************ERROR CHECK for the light going completely dark, what happens??
  }

  return newBrightness;
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


  // Parse JSON
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


  // LED logic:
  // // Turn ON only if percent < 25 AND not plugged in
  // if (percent < 43 && plugged == false) {
  //   alertActive = true;
  //   digitalWrite(alertLED, HIGH);
  // } else {
  //   alertActive = false;
  //   digitalWrite(alertLED, LOW);
  // }


  //LED ADJUSTING VARIABLES
  static unsigned long lastUpdate = 0;
  const int interval = 200;   // ms between dim steps
  const int step = 10;        // how much to dim each step

  if (!plugged && percent < 43) {

    if (millis() - lastUpdate >= interval) {
      lastUpdate = millis();

      currentBrightness = dim_light(currentBrightness, step);
      ledcWrite(pwmChannel, currentBrightness);
    }

    alertActive = true;

  } else {
    // reset when condition not met
    currentBrightness = 255;           // start bright again next time
    ledcWrite(pwmChannel, currentBrightness);
    alertActive = false;
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


      // Subscribe to your unified topic
      client.subscribe("devices/battery");
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

  ledcSetup(pwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(alertLED, pwmChannel);
  ledcWrite(pwmChannel, 0);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  current_brightness = 255;
}


// -----------------------------
// Loop
// -----------------------------
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}
