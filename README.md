# SPECTER

A handheld 2.4GHz RF toolkit built on the Raspberry Pi Pico W. SPECTER is an open source firmware and hardware project that lets you scan, monitor and analyze the 2.4GHz radio band using an NRF24L01+PA+LNA module and a small OLED display.

Built and designed by [Phillip Rødseth](https://kjern.no) / Kjern.no.

---

## What it does

- **2.4GHz Spectrum Analyzer** -- live bar graph of the entire 2.4GHz band (2402-2480MHz), with peak markers and hit counter
- **WiFi Scanner** -- scans nearby WiFi networks using the Pico W built in radio, shows SSID, signal strength and channel
- **BT Monitor** -- watches the three BLE advertising channels (37, 38, 39) and shows activity as live bar charts
- **Signal Meter** -- point the antenna at a source and watch signal strength in real time, tunable by channel
- **Hop Counter** -- counts BLE channel hops per second with a scrolling 20 second history graph
- **System Stats** -- 7 pages of real hardware stats including battery voltage, CPU temp, RAM, flash, NRF status, WiFi MAC and chip ID
- **Settings** -- adjustable scan speed, bar decay, brightness, buzzer on/off, WiFi setup
- **OTA Updates** -- connects to specter.kjern.no to check for and install firmware updates over WiFi

---

## Hardware

| Component | Value |
|-----------|-------|
| Microcontroller | Raspberry Pi Pico W |
| Display | SSD1306 0.96" OLED I2C 128x64 |
| Radio | NRF24L01+PA+LNA |
| Battery | Single cell 3.7V LiPo (1800-2500mAh) |
| Charger | TP4056 module |
| Buttons | Tactile push switches x5 |
| Buzzer | Passive piezo buzzer |
| Decoupling cap | 10µF (NRF VCC) |
| Voltage divider | 2x 100kΩ (battery ADC sense) |

### Building

For wiring instructions, see **[hardware/WIRING.md](hardware/WIRING.md)**.
This is the recommended starting point for building SPECTER from scratch.
It lists every connection in plain language with safety notes and tips.

The KiCad schematic **[hardware/SPECTER.kicad_sch](hardware/SPECTER.kicad_sch)** and
exported PDF **[hardware/SCHEMATICS.pdf](hardware/SCHEMATICS.pdf)** are also available
for those who want a deeper technical view of the circuit. The schematic is significantly
harder to follow than WIRING.md, so start there first.

> The battery, charging and ADC sensing section is the most critical part of the build.
> Read WIRING.md carefully before connecting anything in that area.

---

## Firmware

SPECTER runs on MicroPython. The folder structure is:

```
main.py              entry point
core/                hardware drivers, power, buttons, battery, buzzer, storage, lang
core/languages/      translation files (strings.json)
modules/             third party modules (ssd1306)
screens/             one file per screen
data/                created on first boot, stores settings and persistent data as JSON
hardware/            schematic, wiring guide and KiCad files
```

### Installing

1. Flash MicroPython onto your Pico W from [micropython.org](https://micropython.org/download/RPI_PICO_W/)
2. Copy all files and folders to the Pico W using Thonny or rshell
3. Make sure the folder structure matches the layout above
4. Run main.py or let it run automatically on boot

### Button layout

| Button | Function |
|--------|----------|
| UP | Scroll up / increase value |
| DOWN | Scroll down / decrease value |
| SELECT | Enter screen / confirm |
| BACK | Exit screen / cancel |
| POWER (GP6) | Hold 2 seconds to shut down, press to wake |

---

## License

SPECTER is licensed under the **CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0)**.

See [LICENSE](LICENSE) for the full licence text and [NOTICE.md](NOTICE.md) for attribution requirements.

In short: you can use, modify and sell products based on SPECTER as long as you credit
Kjern.no and keep the source open. If your product has a display, it must show
"SPECTER, by Kjern" or equivalent on the boot screen. See NOTICE.md for the full rules.

---

## Attribution

If you build a product using SPECTER firmware, you must comply with the attribution
requirements in [NOTICE.md](NOTICE.md). This includes crediting Kjern.no on the boot
screen. This attribution must not imply that Kjern.no or SPECTER endorses or sponsors
your product.

---

*Kjern.no -- kjern.no*
