const int NUM_REG = 12;
// byte registers[NUM_REG];
unsigned long start;
unsigned long duration;

void setup() {
  // put your setup code here, to run once:
      // PORTD
    DDRD |=
        (1 << 0) |
        (1 << 1) |
        (1 << 4) |
        (1 << 6) |
        (1 << 7);

    // PORTB
    DDRB |=
        (1 << 4) |
        (1 << 5) |
        (1 << 6) |
        (1 << 7);

    // PORTC
    DDRC |=
        (1 << 6) |
        (1 << 7);

    // PORTE
    DDRE |= (1 << 6);

    // A0 = PF7 clock
    DDRF |= (1 << 7);
}

void loop() {
  if (Serial.available() >= 1) {
    uint8_t numConfigs = Serial.read();
    static uint8_t allData[128 * NUM_REG];
    while (Serial.available() < numConfigs * NUM_REG);
    Serial.readBytes(allData, numConfigs * NUM_REG);

    for (uint8_t c = 0; c < numConfigs; c++) {
        
        // while (Serial.available() < NUM_REG); // wait for full block


        // registers[0] = Serial.read(); 
        // registers[1] = Serial.read(); 
        // registers[2] = Serial.read(); 
        // registers[3] = Serial.read(); 
        // registers[4] = Serial.read(); 
        // registers[5] = Serial.read(); 
        // registers[6] = Serial.read(); 
        // registers[7] = Serial.read(); 
        // registers[8] = Serial.read(); 
        // registers[9] = Serial.read(); 
        // registers[10] = Serial.read(); 
        // registers[11] = Serial.read(); 

        writeRegisters(&allData[c * NUM_REG]);

    }
    Serial.write(0x06); // ACK byte
  }
}

void writeRegisters(uint8_t* registers)
{
    // Local copies kept in CPU registers
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

    // Preserve unrelated bits
    uint8_t pdBase = PORTD & ~(
        (1 << 0) | // pin 3
        (1 << 1) | // pin 2
        (1 << 4) | // pin 4
        (1 << 6) | // pin 12
        (1 << 7)   // pin 6
    );

    uint8_t pbBase = PORTB & ~(
        (1 << 4) | // pin 8
        (1 << 5) | // pin 9
        (1 << 6) | // pin 10
        (1 << 7)   // pin 11
    );

    uint8_t pcBase = PORTC & ~(
        (1 << 6) | // pin 5
        (1 << 7)   // pin 13
    );

    uint8_t peBase = PORTE & ~(1 << 6); // pin 7

    for(uint8_t i = 0; i < 8; i++)
    {
        // delay(2000);
        
        uint8_t pd = pdBase;
        uint8_t pb = pbBase;
        uint8_t pc = pcBase;
        uint8_t pe = peBase;

        // Pin 2 -> PD1
        if(r0 & 0x80) pd |= (1 << 1);

        // Pin 3 -> PD0
        if(r1 & 0x80) pd |= (1 << 0);

        // Pin 4 -> PD4
        if(r2 & 0x80) pd |= (1 << 4);

        // Pin 5 -> PC6
        if(r3 & 0x80) pc |= (1 << 6);

        // Pin 6 -> PD7
        if(r4 & 0x80) pd |= (1 << 7);

        // Pin 7 -> PE6
        if(r5 & 0x80) pe |= (1 << 6);

        // Pin 8 -> PB4
        if(r6 & 0x80) pb |= (1 << 4);

        // Pin 9 -> PB5
        if(r7 & 0x80) pb |= (1 << 5);

        // Pin 10 -> PB6
        if(r8 & 0x80) pb |= (1 << 6);

        // Pin 11 -> PB7
        if(r9 & 0x80) pb |= (1 << 7);

        // Pin 12 -> PD6
        if(r10 & 0x80) pd |= (1 << 6);

        // Pin 13 -> PC7
        if(r11 & 0x80) pc |= (1 << 7);

        // Write ports
        PORTD = pd;
        PORTB = pb;
        PORTC = pc;
        PORTE = pe;

        // Clock pulse on A0 = PF7
        PORTF |=  (1 << 7);
        PORTF &= ~(1 << 7);

        // Shift for next bit
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
