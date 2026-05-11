const int NUM_REG = 12;
// static int index = 0;
byte registers[NUM_REG];

void setup()
{
  // Set pins 2-7 as output (PORTD)
  DDRD |= 0b11111100;

  // Set pins 8-13 as output (PORTB)
  DDRB |= 0b00111111;

  // Set A0 as output (PORTC0)
  DDRC |= (1 << 0);

  Serial.begin(115200);   // faster baud
}

void loop() {

  if(Serial.available() >= NUM_REG)
  {

    for(int i=0;i<NUM_REG;i++){
      registers[i] = Serial.read();
    }

    writeRegisters();
    Serial.println("");
  }
}

void writeRegisters()
{
  for(int bit = 7; bit >= 0; bit--)
  {
    uint8_t portDValue = 0;
    uint8_t portBValue = 0;

    // Registers 0-5 → pins 2-7 → PORTD
    for(int r=0; r<6; r++)
    {
      if ((registers[r] >> bit) & 1)
        portDValue |= (1 << (r + 2));
    }

    // Registers 6-11 → pins 8-13 → PORTB
    for(int r=6; r<12; r++)
    {
      if ((registers[r] >> bit) & 1)
        portBValue |= (1 << (r - 6));
    }

    PORTD = (PORTD & 0b00000011) | portDValue;
    PORTB = (PORTB & 0b11000000) | portBValue;

    // Clock pulse on A0 (PORTC0)
    PORTC |= (1 << 0);
    PORTC &= ~(1 << 0);
  }
}