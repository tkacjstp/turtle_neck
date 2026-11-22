const byte RED_PIN = 9;
const byte GREEN_PIN = 10;
const byte BLUE_PIN = 11;
const byte BUZZER_PIN = 3;
const bool COMMON_ANODE = false;
const bool PASSIVE_BUZZER = false;
const bool BUZZER_ACTIVE_HIGH = true;
char status = 'O';
unsigned long changed = 0;
unsigned long lastMessage = 0;
bool buzzing = false;

void rgb(bool red, bool green, bool blue) {
  digitalWrite(RED_PIN, red != COMMON_ANODE);
  digitalWrite(GREEN_PIN, green != COMMON_ANODE);
  digitalWrite(BLUE_PIN, blue != COMMON_ANODE);
}

void buzzer(bool on) {
  if (PASSIVE_BUZZER) {
    if (on) tone(BUZZER_PIN, 880);
    else noTone(BUZZER_PIN);
  } else {
    digitalWrite(BUZZER_PIN, on == BUZZER_ACTIVE_HIGH);
  }
}

void setup() {
  rgb(false, false, false);
  buzzer(false);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  unsigned long now = millis();
  while (Serial.available()) {
    char command = Serial.read();
    if (command != 'N' && command != 'W' && command != 'D' && command != 'O') continue;
    lastMessage = now;
    if (command != status) {
      status = command;
      changed = now;
    }
  }
  if (now - lastMessage >= 2000) status = 'O';
  unsigned long phase = (now - changed) % 1000;
  bool warning = status == 'W' && phase < 500;
  rgb(status == 'D' || warning, status == 'N' || warning, false);
  bool nextBuzz = status == 'D' && phase < 200;
  if (nextBuzz != buzzing) {
    buzzer(nextBuzz);
    buzzing = nextBuzz;
  }
}
