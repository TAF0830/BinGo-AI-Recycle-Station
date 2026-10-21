// ESP32-S3 Waste Classification Controller (BinGo / SmartSort Station)
// Aligned with Python Vision CMD_MAP:
// 1 -> FOOD WASTE
// 2 -> GENERAL WASTE
// 3 -> RECYCLABLE WASTE
// 4 -> SPECIAL WASTE
// 0 -> BACKGROUND / IDLE

const int PIN_FOOD        = 4; // GPIO 4 (Food Waste Indicator)
const int PIN_GENERAL     = 5; // GPIO 5 (General Waste Indicator)
const int PIN_RECYCLABLE  = 6; // GPIO 6 (Recyclable Waste Indicator)
const int PIN_SPECIAL     = 7; // GPIO 7 (Special Waste Indicator)

void turnOffAll() {
  digitalWrite(PIN_FOOD, LOW);
  digitalWrite(PIN_GENERAL, LOW);
  digitalWrite(PIN_RECYCLABLE, LOW);
  digitalWrite(PIN_SPECIAL, LOW);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_FOOD, OUTPUT);
  pinMode(PIN_GENERAL, OUTPUT);
  pinMode(PIN_RECYCLABLE, OUTPUT);
  pinMode(PIN_SPECIAL, OUTPUT);

  // Power-on self-test (LED sequence)
  turnOffAll();
  digitalWrite(PIN_FOOD, HIGH); delay(150); digitalWrite(PIN_FOOD, LOW);
  digitalWrite(PIN_GENERAL, HIGH); delay(150); digitalWrite(PIN_GENERAL, LOW);
  digitalWrite(PIN_RECYCLABLE, HIGH); delay(150); digitalWrite(PIN_RECYCLABLE, LOW);
  digitalWrite(PIN_SPECIAL, HIGH); delay(150); digitalWrite(PIN_SPECIAL, LOW);
  turnOffAll();

  Serial.println("\nESP32-S3 BinGo Station Controller Ready!");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    // Filter newline and whitespace characters
    if (cmd == '\r' || cmd == '\n' || cmd == ' ') return;

    turnOffAll(); // Clear previous states before setting new indicator

    switch (cmd) {
      case '1':
        digitalWrite(PIN_FOOD, HIGH);
        Serial.println("Action: Food Waste (GPIO 4)");
        break;
      case '2':
        digitalWrite(PIN_GENERAL, HIGH);
        Serial.println("Action: General Waste (GPIO 5)");
        break;
      case '3':
        digitalWrite(PIN_RECYCLABLE, HIGH);
        Serial.println("Action: Recyclable Waste (GPIO 6)");
        break;
      case '4':
        digitalWrite(PIN_SPECIAL, HIGH);
        Serial.println("Action: Special Waste (GPIO 7)");
        break;
      case '0':
        Serial.println("Action: Reset / Background (All Off)");
        break;
    }
  }
}
