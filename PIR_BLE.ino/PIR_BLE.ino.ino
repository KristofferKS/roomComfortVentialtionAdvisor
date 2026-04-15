// ESP32-C6-WROOM-1 + ST-00081 PIR Motion Sensor
// PIR output → GPIO 6
// BLE server advertising motion state

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#define PIR_PIN 6

//  service UUID
#define SERVICE_UUID              "7e2f6a91-8c3d-4b2a-9f6e-1c4d8a7b5e92"

//  characteristic UUID just for PIR motion
#define CHARACTERISTIC_UUID_PIR   "a1b2c3d4-1234-5678-abcd-a1b2c3d4e5f6"

BLECharacteristic *pPirCharacteristic;

bool deviceConnected    = false;
bool oldDeviceConnected = false;
int  lastMotionState    = -1; // Force first update on boot

class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *pServer) {
    deviceConnected = true;
    Serial.println("Device connected");
  }
  void onDisconnect(BLEServer *pServer) {
    deviceConnected = false;
    Serial.println("Device disconnected");
  }
};

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("PIR motion sensor ready.");

  // BLE Setup
  BLEDevice::init("ESP32_PIR");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  // PIR motion characteristic
  pPirCharacteristic = pService->createCharacteristic(
    CHARACTERISTIC_UUID_PIR,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
  );
  pPirCharacteristic->addDescriptor(new BLE2902());
  pPirCharacteristic->setValue("motion:0");

  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();
  Serial.println("BLE server started, advertising...");
}

void loop() {
  int motion = digitalRead(PIR_PIN);

  // Only act on state change
  if (motion != lastMotionState) {
    lastMotionState = motion;

    if (motion == HIGH) {
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("Motion detected!");
      pPirCharacteristic->setValue("motion:1");
    } else {
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("No motion.");
      pPirCharacteristic->setValue("motion:0");
    }

    // Notify connected client of motion change immediately
    if (deviceConnected) {
      pPirCharacteristic->notify();
    }
  }

  // Handle reconnection
  if (!deviceConnected && oldDeviceConnected) {
    delay(500);
    BLEDevice::startAdvertising();
    Serial.println("Restarted advertising");
    oldDeviceConnected = false;
  }

  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = true;
  }

  delay(100);
}
