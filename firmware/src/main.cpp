#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>

// TFG Desarrollo de aplicaciones electrónicas. Borja Sánchez Rodríguez.
// Código del firmware para el ESP32. 
// Control lógico de todo el sistema con comunicación serie con la GUI en Python.
// Se implementan las funciones para los test de tensión Zener y corriente de fugas.

// ======== Pines I2C ========
// Configurados los pines de datos y reloj para el bus I2C.
#define SDA_PIN 8
#define SCL_PIN 9

// ======== DACs ========
//Librería específica para los MCP4725
Adafruit_MCP4725 dacV; 
Adafruit_MCP4725 dacI;

// ======== Pines ESP32 ========
// Pines físicos de la placa
const int PIN_ADC_VMON = 1;
const int PIN_ADC_I    = 2;
const int PIN_RELE     = 4;

// ======== Constantes ========
const float VREF      = 3.3f; //Float para ahorro de memoria
const float DAC_MAX   = 4095.0f; //12 bits de los DACs/ADC
const float ADC_MAX   = 4095.0f;
const float GAIN      = 40.0f; //Ganancia AO
const float R_SHUNT   = 1000.0f;
const float VMON_SCALE = 16.07f;  // Escala ADC, 0-75V -> 0-5V (limitado a 3.3V)

// ======== Consignas analógicas ========
// Escalas de las consignas para la fuente de alimentación.
// Escala fuente 0-5V -> 0-75V, Maximo 3.3V por el ESP32
const float VPROG_ZENER       = 1.630f;  //  24.0 V (ambos diodos)
const float VPROG_FUGAS_GREEN = 1.326f;  //  19.7 V
const float VPROG_FUGAS_BLUE  = 1.421f;  //  21.1 V
const float IPROG             = 0.275f;  // 100mA para limitar fuente

// ======== TestState ========
// Variables para comprobar e inicializar el estado del test para poder comenzar o parar pruebas.
int  currentTest = 0;
bool testRunning = false;

// ======== Inicialización del sistema ========
// Setup del controlador, periféricos y estado inciial del sistema.
void setup() {
  Serial.begin(115200);
  delay(500);

  //Inicializar bus I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  //Direccionamiento DACs por I2C
  dacV.begin(0x60);
  dacI.begin(0x61);
  
  //Inicialización del sistema, normalizado a 0
  dacV.setVoltage(0, false);
  dacI.setVoltage(0, false);

  // Relé en reposo
  pinMode(PIN_RELE, OUTPUT);
  digitalWrite(PIN_RELE, LOW);
  analogReadResolution(12); //4095 niveles para ADC de 12 bits

  Serial.println("ESP32 listo");
}

// ======== Funciones DACs ========
// Función para el escalado del voltaje de consigna.
uint16_t voltageToDAC(float v) {
  if (v < 0)    v = 0; //Valores seguros
  if (v > VREF) v = VREF;
  return (uint16_t)(v / VREF * DAC_MAX); //Escalado
}

// Salidas analógicas para fuente
void setVprog(float v) { 
  dacV.setVoltage(voltageToDAC(v), false); 
}

void setIprog(float v) { 
  dacI.setVoltage(voltageToDAC(v), false); 
}

// ======== Funciones ADC ========
// Funciones para el escalado de las lectuas de los ADC.
// Vmon desde fuente
float readVmon() {
  float Vadc = (analogRead(PIN_ADC_VMON) / ADC_MAX) * VREF;
  return Vadc * VMON_SCALE;
}

// Ir, fugas desde circuito amplificador
float readIr() {
  float Vadc   = (analogRead(PIN_ADC_I) / ADC_MAX) * VREF;
  float Vshunt = Vadc / GAIN;
  return (Vshunt / R_SHUNT) * 1e6f; //Amperios a microamperios
}

// ======== StopTest ========
// Función para detener las pruebas.
void stopAll() {
  testRunning = false;
  currentTest = 0;
  setVprog(0);
  setIprog(0);
  digitalWrite(PIN_RELE, LOW);
  Serial.println("STOPPED");
}

// ======== StartTest ========
// Función para inciiar el test seleccionado.
// 0 = diodo verde, 1 = diodo azul
void startTest(int test, int diode) {
  //Aseguramos fuente en reposo 
  setVprog(0);
  setIprog(0);
  delay(100);

  currentTest = test;

  if (test == 1) {
    // Prueba tensión Zener: 24V en ambos diodos, relé LOW
    digitalWrite(PIN_RELE, LOW);
    delay(50);
    setIprog(IPROG);
    setVprog(VPROG_ZENER);
    Serial.println("TEST1_STARTED");
  }
  else if (test == 2) {
    // Prueba corriente de fugas: tensión Zener - 1.3V, relé HIGH
    digitalWrite(PIN_RELE, HIGH);
    delay(50);
    setIprog(IPROG);
    float vprog;
    if (diode == 0) {
        vprog = VPROG_FUGAS_GREEN;
    } else {
        vprog = VPROG_FUGAS_BLUE;
    }
    setVprog(vprog);
    Serial.println("TEST2_STARTED");
  }

  testRunning = true;
}

// ======== Bucle principal ========
// Loop principal del firmware.
// Encargado de la lectura/escritura de los prompt de la comunicación serie.
void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // Comunicación serie para la GUI 
    if      (cmd == "START1_GREEN") startTest(1, 0);
    else if (cmd == "START1_BLUE")  startTest(1, 1);
    else if (cmd == "START2_GREEN") startTest(2, 0);
    else if (cmd == "START2_BLUE")  startTest(2, 1);
    else if (cmd == "STOP")         stopAll();
  }

  // Print de resultados
  if (testRunning) {
    if (currentTest == 1) {
      float v = readVmon();
      Serial.print("VOLT:");
      Serial.println(v, 2);
    }
    else if (currentTest == 2) {
      float v = readVmon();
      float i = readIr();
      Serial.print("VOLT:");
      Serial.print(v, 2);
      Serial.print(",I:");
      Serial.println(i, 3);
    }
    delay(200);
  }
}