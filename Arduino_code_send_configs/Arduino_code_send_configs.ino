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

  Serial.begin(500000);   // baud
}

void loop() {

  if(Serial.available() >= NUM_REG)
  {
    Serial.readBytes(registers, NUM_REG);

    writeRegisters();

    Serial.write(0x06); // ACK byte
  }
}

void writeRegisters()
{
  for(int bit = 7; bit >= 0; bit--)
  {
    uint8_t d = 0;
    uint8_t b = 0;

    d |= ((registers[0] >> bit) & 1) << 2;
    d |= ((registers[1] >> bit) & 1) << 3;
    d |= ((registers[2] >> bit) & 1) << 4;
    d |= ((registers[3] >> bit) & 1) << 5;
    d |= ((registers[4] >> bit) & 1) << 6;
    d |= ((registers[5] >> bit) & 1) << 7;

    b |= ((registers[6] >> bit) & 1) << 0;
    b |= ((registers[7] >> bit) & 1) << 1;
    b |= ((registers[8] >> bit) & 1) << 2;
    b |= ((registers[9] >> bit) & 1) << 3;
    b |= ((registers[10] >> bit) & 1) << 4;
    b |= ((registers[11] >> bit) & 1) << 5;

    PORTD = (PORTD & 0x03) | d;
    PORTB = (PORTB & 0xC0) | b;

    PORTC |= 1;
    PORTC &= ~1;
  }
}