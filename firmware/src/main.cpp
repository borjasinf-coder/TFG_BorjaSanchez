#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>


// ================== CONFIGURACIÓN I2C ==================
#define SDA_PIN 20
#define SCL_PIN 21

// ================== DACs ==================
Adafruit_MCP4725 dacV;   // Vprog
Adafruit_MCP4725 dacI;   // Iprog

// ================== PINES ==================
const int adcVmon = 34;     // Vmon (fuente)
const int adcI = 35;     // I fugas (shunt)
const int relePin = 26;    // Relé

// ================== CONSTANTES ==================
const float VREF = 3.3;     // ADC y DAC trabajan a 3.3V
const float DAC_MAX = 4095.0;

// Ganancia del amplificador de corriente
const float GAIN = 40.0;

// Shunt
const float R_SHUNT = 1000.0; // 1kΩ

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);

  // Inicializar I2C en pines definidos
  Wire.begin(SDA_PIN, SCL_PIN);

  // Inicializar DACs
  dacV.begin(0x60); // A0 a GND
  dacI.begin(0x61); // segundo DAC

  pinMode(relePin, OUTPUT);
  digitalWrite(relePin, LOW);

  Serial.println("ESP32 listo");
}

// ================== FUNCIONES DAC ==================
uint16_t voltageToDAC(float volts){
  if(volts < 0) volts = 0;
  if(volts > VREF) volts = VREF;
  return (uint16_t)(volts / VREF * DAC_MAX);
}

void setVprog(float volts){
  uint16_t value = voltageToDAC(volts);
  dacV.setVoltage(value, false);
}

void setIprog(float volts){
  uint16_t value = voltageToDAC(volts);
  dacI.setVoltage(value, false);
}

// ================== Medidas ADC ==================
float readVmon(){
  int raw = analogRead(adcVmon);
  return (raw / 4095.0) * VREF;
}

float readCurrent_uA(){
  int raw = analogRead(adcI); //Función de Arduino para leer analogica de pin
  float Vadc = (raw / 4095.0) * VREF;

  float Vshunt = Vadc / GAIN;
  float I = Vshunt / R_SHUNT;

  return I * 1e6;
}

// ================== PRUEBAS ==================
void pruebaZener(){
  Serial.println("START_PRUEBA_1");

  setVprog(0);
  setIprog(0);
  delay(200);

  digitalWrite(relePin, HIGH);

  // Ajustes (modo 3.3V → escala reducida)
  setIprog(0.165);  // equivalente a 10mA escalado
  setVprog(1.18);   // equivalente a 25V escalado

  delay(200);

  float Vmon = readVmon();

  Serial.print("VZENER:");
  Serial.println(Vmon);

  digitalWrite(relePin, LOW);
  Serial.println("END_PRUEBA_1");
}

void pruebaFugas(){
  Serial.println("START_PRUEBA_2");

  setVprog(0);
  setIprog(0);
  delay(200);

  digitalWrite(relePin, HIGH);

  // Ajustes escalados
  setIprog(0.495);   // 300mA escalado
  setVprog(0.97);    // 19.4V escalado

  delay(200);

  float Vmon = readVmon();
  float IuA = readCurrent_uA();

  Serial.print("VMON:");
  Serial.println(Vmon);

  Serial.print("IFUGAS_uA:");
  Serial.println(IuA);

  digitalWrite(relePin, LOW);
  Serial.println("END_PRUEBA_2");
}

// ================== LOOP ==================
void loop(){
  if(Serial.available()){
    String cmd = Serial.readStringUntil('\n');

    cmd.trim();

    if(cmd == "START_PRUEBA_1"){
      pruebaZener();
    }
    else if(cmd == "START_PRUEBA_2"){
      pruebaFugas();
    }
    else if(cmd == "STOP"){
      setVprog(0);
      setIprog(0);
      digitalWrite(relePin, LOW);
      Serial.println("STOPPED");
    }
  }
}