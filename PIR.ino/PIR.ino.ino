// ESP32-C6-WROOM-1 + ST-00081 PIR Motion Sensor
// PIR output → GPIO 18
// Built-in LED → GPIO 8 (ESP32-C6 onboard RGB, blue channel)


#define PIR_PIN     6
int state = LOW;

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("PIR motion sensor ready.");
}

void loop() {
  int motion = digitalRead(PIR_PIN);

  if (motion != state) {
    if (motion == HIGH) {
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("Motion detected!");
    } else {
      digitalWrite(LED_BUILTIN, LOW);
    }
    
  }
  state = motion;

  delay(100); // Small debounce delay
}
