// ESP32-S3 Waste Classification Controller (GPIO 4-7)
// '0' -> STANDBY / BACKGROUND (turn  off led)
// '1' -> FOOD WASTE (GPIO 7 - green led)
// '2' -> GENERAL WASTE (GPIO 6 - yellow led)
// '3' -> RECYCLABLE WASTE (GPIO 5 - white led)
// '4' -> SPECIAL WASTE (GPIO 4 - red led)

const int PIN_SPECIAL    = 4; // GPIO 4 (Special Waste - red led)
const int PIN_RECYCLABLE = 5; // GPIO 5 (Recyclable Waste - white led)
const int PIN_GENERAL    = 6; // GPIO 6 (General Waste - yellow led)
const int PIN_FOOD       = 7; // GPIO 7 (Food Waste - green led)

void turnOffAll() {
  digitalWrite(PIN_SPECIAL, LOW);
  digitalWrite(PIN_RECYCLABLE, LOW);
  digitalWrite(PIN_GENERAL, LOW);
  digitalWrite(PIN_FOOD, LOW);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_SPECIAL, OUTPUT);
  pinMode(PIN_RECYCLABLE, OUTPUT);
  pinMode(PIN_GENERAL, OUTPUT);
  pinMode(PIN_FOOD, OUTPUT);

  
  turnOffAll();
  digitalWrite(PIN_SPECIAL, HIGH);    delay(150); digitalWrite(PIN_SPECIAL, LOW);
  digitalWrite(PIN_RECYCLABLE, HIGH); delay(150); digitalWrite(PIN_RECYCLABLE, LOW);
  digitalWrite(PIN_GENERAL, HIGH);    delay(150); digitalWrite(PIN_GENERAL, LOW);
  digitalWrite(PIN_FOOD, HIGH);       delay(150); digitalWrite(PIN_FOOD, LOW);
  turnOffAll();

  Serial.println("\nESP32-S3 Waste System Ready!");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == '\r' || cmd == '\n' || cmd == ' ') return;

    turnOffAll(); // 

    switch (cmd) {
      case '0': // BACKGROUND / 
        Serial.println("Action: STANDBY (All LEDs OFF)");
        break;

      case '1': // FOOD WASTE -> 绿灯 (GPIO 7)
        digitalWrite(PIN_FOOD, HIGH);
        Serial.println("Action: FOOD WASTE on GPIO 7 (Green)");
        break;

      case '2': // GENERAL WASTE -> yellow led (GPIO 6)
        digitalWrite(PIN_GENERAL, HIGH);
        Serial.println("Action: GENERAL WASTE on GPIO 6 (Yellow)");
        break;

      case '3': // RECYCLABLE WASTE -> white led (GPIO 5)
        digitalWrite(PIN_RECYCLABLE, HIGH);
        Serial.println("Action: RECYCLABLE WASTE on GPIO 5 (Blue)");
        break;

      case '4': // SPECIAL WASTE -> red led (GPIO 4)
        digitalWrite(PIN_SPECIAL, HIGH);
        Serial.println("Action: SPECIAL WASTE on GPIO 4 (Red)");
        break;

      default:
        break;
    }
  }
}
