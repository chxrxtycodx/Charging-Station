void setup() {
  // put your setup code here, to run once:
  const int trigPin = 14;
  const int echoPin = 15;
  float duration, distance;
}

void loop() {
  // put your main code here, to run repeatedly:
  // ranger reading
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH);
  distance = (duration*.0343)/2;
}
