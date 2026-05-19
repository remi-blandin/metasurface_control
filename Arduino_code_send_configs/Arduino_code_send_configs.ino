const int NUM_REG = 12;
byte registers[NUM_REG];
unsigned long start;
unsigned long duration;

void setup()
{
  // Set pins 2-7 as output (PORTD)
  DDRD |= 0b11111100;

  // Set pins 8-13 as output (PORTB)
  DDRB |= 0b00111111;

  // Set A0 as output (PORTC0)
  DDRC |= (1 << 0);

  Serial.begin(1000000);   // baud
}

void loop() {

  if(Serial.available() >= NUM_REG)
  {
    // track execution time
    start = micros();

    registers[0] = Serial.read(); 
    registers[1] = Serial.read(); 
    registers[2] = Serial.read(); 
    registers[3] = Serial.read(); 
    registers[4] = Serial.read(); 
    registers[5] = Serial.read(); 
    registers[6] = Serial.read(); 
    registers[7] = Serial.read(); 
    registers[8] = Serial.read(); 
    registers[9] = Serial.read(); 
    registers[10] = Serial.read(); 
    registers[11] = Serial.read(); 

    writeRegisters();

    duration = micros() - start;

    Serial.println(duration);

    // Serial.write(0x06); // ACK byte
  }
}

  void writeRegisters()
{
    uint8_t r0  = registers[0];
    uint8_t r1  = registers[1];
    uint8_t r2  = registers[2];
    uint8_t r3  = registers[3];
    uint8_t r4  = registers[4];
    uint8_t r5  = registers[5];
    uint8_t r6  = registers[6];
    uint8_t r7  = registers[7];
    uint8_t r8  = registers[8];
    uint8_t r9  = registers[9];
    uint8_t r10 = registers[10];
    uint8_t r11 = registers[11];

    uint8_t pd = PORTD & 0x03;
    uint8_t pb = PORTB & 0xC0;

    for(uint8_t i = 0; i < 8; i++)
    {
        uint8_t d = 0;
        uint8_t b = 0;

        if(r0  & 0x80) d |= (1 << 2);
        if(r1  & 0x80) d |= (1 << 3);
        if(r2  & 0x80) d |= (1 << 4);
        if(r3  & 0x80) d |= (1 << 5);
        if(r4  & 0x80) d |= (1 << 6);
        if(r5  & 0x80) d |= (1 << 7);

        if(r6  & 0x80) b |= (1 << 0);
        if(r7  & 0x80) b |= (1 << 1);
        if(r8  & 0x80) b |= (1 << 2);
        if(r9  & 0x80) b |= (1 << 3);
        if(r10 & 0x80) b |= (1 << 4);
        if(r11 & 0x80) b |= (1 << 5);

        PORTD = pd | d;
        PORTB = pb | b;

        // Arduino Uno
        PORTC |= _BV(0);
        PORTC &= ~_BV(0);

        r0 <<= 1;
        r1 <<= 1;
        r2 <<= 1;
        r3 <<= 1;
        r4 <<= 1;
        r5 <<= 1;

        r6 <<= 1;
        r7 <<= 1;
        r8 <<= 1;
        r9 <<= 1;
        r10 <<= 1;
        r11 <<= 1;
    }
}