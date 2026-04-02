# SPECTER Wiring Guide

This is the recommended file to follow if you are building SPECTER from scratch.
The KiCad schematic (specter.kicad_sch) contains the same information but is significantly
harder to follow, especially if you are not familiar with reading schematics.
The schematic is there for people who want a deeper technical understanding of the circuit.
This file is for everyone else :)

---

## Before you start

**Read this section before connecting anything.**

### Battery safety
- Only use a **single cell 3.7V nominal LiPo battery**. Do not use 2S or higher packs.
- Connect the battery to the **VSYS pin (pin 39)** only, never to VBUS or the 3.3V rail.
  The reason is that the Pico W has a built in buck-boost regulator on VSYS that accepts
  1.8V to 5.5V and always outputs a stable 3.3V to the rest of the board. If you connect
  directly to the 3.3V rail you bypass this regulator entirely and the voltage will sag
  as the battery drains, causing unpredictable behaviour and possibly damaging the Pico.
  VSYS is designed exactly for this use case, always use it.
- Charge the battery through a **TP4056 module** only, never connect a charger directly
  to the battery or to VSYS while the Pico is running without a protection circuit.

### Voltage divider warning
The voltage divider on GP28 is extremely important and must be built correctly.
A fully charged LiPo outputs 4.2V which will damage the Pico W ADC pin if connected
directly since the ADC only handles up to 3.3V maximum.

The two 100kΩ resistors form a divider that halves the voltage:
4.2V becomes 2.1V, 3.7V becomes 1.85V, 3.0V becomes 1.5V -- all safe for the ADC.

**If you are new to voltage dividers, do the following before connecting to GP28:**
1. Build the divider on the bench with the battery connected
2. Measure the voltage at the midpoint (junction between the two resistors) with a multimeter
3. It should be roughly half the battery voltage
4. Only connect to GP28 once you have confirmed this

Getting this wrong will not cause a fire but it will permanently damage the ADC on your Pico.

---

## Wiring

### OLED Display (SSD1306, I2C)
```
OLED VCC  →  3.3V
OLED GND  →  GND
OLED SDA  →  GP0
OLED SCL  →  GP1
```

### NRF24L01+PA+LNA Radio Module
```
NRF VCC   →  3.3V
NRF GND   →  GND
NRF SCK   →  GP10
NRF MOSI  →  GP11
NRF MISO  →  GP12
NRF CSN   →  GP14
NRF CE    →  GP17
```
Add a **10µF capacitor** between NRF VCC and GND, placed as close to the module pins
as possible. The NRF draws sudden current bursts when the radio is active and without
this cap the supply voltage dips momentarily causing init failures and corrupted SPI reads.
This capacitor is not optional if you want reliable behaviour.

### Navigation Buttons (x5)
Each button has one leg on the GP pin and the other leg on 3V3.
No external resistors needed, the firmware uses internal pull-downs.
```
UP button      →  GP2  and 3V3
DOWN button    →  GP3  and 3V3
SELECT button  →  GP4  and 3V3
BACK button    →  GP5  and 3V3
POWER button   →  GP6  and 3V3
```

### Piezo Buzzer
```
Buzzer +  →  GP18
Buzzer -  →  GND
```
A 10kΩ pull-down resistor between GP18 and GND is optional. The firmware drives the pin
explicitly so it should stay silent when not active. However on some passive buzzers the
pin floating slightly can cause a faint continuous tone. If you experience this, add the
pull-down. Mark it DNP (do not populate) if you are making a PCB and only fit it if needed.

### Battery
```
Battery +  →  VSYS (Pico W pin 39)
Battery -  →  GND
```
See the battery safety note at the top of this file before connecting.

### Battery Voltage Sense (Voltage Divider)
```
Battery +  →  100kΩ  →  GP28  →  100kΩ  →  GND
```
The junction between the two resistors connects to GP28.
See the voltage divider warning at the top of this file before connecting.

### TP4056 Charging Module
```
TP4056 B+   →  Battery +
TP4056 B-   →  Battery -
```

---

## Pin summary

| GP Pin | Connected to         |
|--------|----------------------|
| GP0    | OLED SDA             |
| GP1    | OLED SCL             |
| GP2    | Button UP            |
| GP3    | Button DOWN          |
| GP4    | Button SELECT        |
| GP5    | Button BACK          |
| GP6    | Button POWER         |
| GP10   | NRF SCK              |
| GP11   | NRF MOSI             |
| GP12   | NRF MISO             |
| GP14   | NRF CSN              |
| GP17   | NRF CE               |
| GP18   | Buzzer +             |
| GP28   | Battery ADC (via divider) |

---

## Components list

| Component              | Value / Part          |
|------------------------|-----------------------|
| Microcontroller        | Raspberry Pi Pico W   |
| Display                | SSD1306 0.96" OLED I2C 128x64 |
| Radio module           | NRF24L01+PA+LNA       |
| Battery                | Single cell 3.7V LiPo (1800-2500mAh recommended) |
| Charger                | TP4056 module         |
| Buttons                | Tactile push switches x5 |
| Buzzer                 | Active piezo buzzer 3.3V |
| Decoupling cap (NRF)   | 10µF electrolytic or ceramic |
| Voltage divider R1     | 100kΩ 1/4W            |
| Voltage divider R2     | 100kΩ 1/4W            |
| Pull-down (buzzer)     | 10kΩ 1/4W (optional, see buzzer section) |
