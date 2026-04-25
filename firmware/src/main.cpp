#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>

// ================== I2C ==================
#define SDA_PIN 8
#define SCL_PIN 9

// ================== DACs ==================
Adafruit_MCP4725 dacV;
Adafruit_MCP4725 dacI;

// ================== PINES ==================
const int adcVmon = 1;
const int adcI    = 2;
const int relePin = 4;

// ================== CONSTANTES ==================
const float VREF      = 3.3f;
const float DAC_MAX   = 4095.0f;
const float ADC_MAX   = 4095.0f;
const float GAIN      = 40.0f;
const float R_SHUNT   = 1000.0f;

// Escala ADC: el divisor resistivo lleva 0-75V → 0-3.3V
const float VMON_SCALE = 16.07f;

// ================== CONSIGNAS ==================
// Vprog: escala fuente 0-5V → 0-75V, DAC sale 0-3.3V
// Vprog (V) = V_salida_deseada / 75 * 5
const float VPROG_ZENER       = 1.630f;  // → 24.0 V (ambos diodos)
const float VPROG_FUGAS_GREEN = 1.326f;  // → 19.7 V
const float VPROG_FUGAS_BLUE  = 1.421f;  // → 21.1 V
const float IPROG             = 0.275f;  // mismo para todos

// ================== ESTADO ==================
int  currentTest = 0;
bool testRunning = false;

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  delay(500);

  //Inicializar I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  dacV.begin(0x60);
  dacI.begin(0x61);

  dacV.setVoltage(0, false);
  dacI.setVoltage(0, false);

  pinMode(relePin, OUTPUT);
  digitalWrite(relePin, LOW);
  analogReadResolution(12);

  Serial.println("ESP32 listo");
}

// ================== DAC ==================
uint16_t voltageToDAC(float v) {
  if (v < 0)    v = 0;
  if (v > VREF) v = VREF;
  return (uint16_t)(v / VREF * DAC_MAX);
}
void setVprog(float v) { dacV.setVoltage(voltageToDAC(v), false); }
void setIprog(float v) { dacI.setVoltage(voltageToDAC(v), false); }

// ================== ADC ==================
float readVmon() {
  float Vadc = (analogRead(adcVmon) / ADC_MAX) * VREF;
  return Vadc * VMON_SCALE;   // devuelve voltios reales (0-75V)
}
float readIuA() {
  float Vadc   = (analogRead(adcI) / ADC_MAX) * VREF;
  float Vshunt = Vadc / GAIN;
  return (Vshunt / R_SHUNT) * 1e6f;
}

// ================== PARAR TODO ==================
void stopAll() {
  testRunning = false;
  currentTest = 0;
  setVprog(0);
  setIprog(0);
  digitalWrite(relePin, LOW);
  Serial.println("STOPPED");
}

// ================== INICIAR PRUEBA ==================
// diode: 0 = verde, 1 = azul
void startTest(int test, int diode) {
  setVprog(0);
  setIprog(0);
  delay(100);

  currentTest = test;

  if (test == 1) {
    // Prueba Zener: 24V en ambos diodos, relé LOW
    digitalWrite(relePin, LOW);
    delay(50);
    setIprog(IPROG);
    setVprog(VPROG_ZENER);
    Serial.println("TEST1_STARTED");
  }
  else if (test == 2) {
    // Prueba Fugas: tensión según diodo, relé HIGH
    digitalWrite(relePin, HIGH);
    delay(50);
    setIprog(IPROG);
    float vp = (diode == 0) ? VPROG_FUGAS_GREEN : VPROG_FUGAS_BLUE;
    setVprog(vp);
    Serial.println("TEST2_STARTED");
  }

  testRunning = true;
}

// ================== LOOP ==================
void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if      (cmd == "START1_GREEN") startTest(1, 0);
    else if (cmd == "START1_BLUE")  startTest(1, 1);
    else if (cmd == "START2_GREEN") startTest(2, 0);
    else if (cmd == "START2_BLUE")  startTest(2, 1);
    else if (cmd == "STOP")         stopAll();
  }

  if (testRunning) {
    if (currentTest == 1) {
      float v = readVmon();
      Serial.print("VOLT:");
      Serial.println(v, 2);
    }
    else if (currentTest == 2) {
      float v = readVmon();
      float i = readIuA();
      Serial.print("VOLT:");
      Serial.print(v, 2);
      Serial.print(",I:");
      Serial.println(i, 3);
    }
    delay(200);
  }
}