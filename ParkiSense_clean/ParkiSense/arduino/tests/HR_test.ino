#include <Wire.h>

void setup() {
  Serial.begin(115200);
  while (!Serial); // Espera a que abras el monitor serie
 
  Wire.begin();
  Serial.println("Iniciando sensor de Ritmo Cardíaco...");
  Serial.println("Ponte el clip en el dedo y quédate quieto 15 segundos.");
}

void loop() {
  // Pedimos 1 byte al dispositivo en la dirección 0x50
  Wire.requestFrom(0x50, 1);    
 
  // Si el sensor responde, leemos el byte
  if(Wire.available()) {          
    unsigned char bpm = Wire.read();
   
    Serial.print("Latidos por minuto: ");
    Serial.println(bpm, DEC);
  }
 
  // Esperamos medio segundo antes de pedir la siguiente lectura
  delay(500);
}
