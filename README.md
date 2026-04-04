# SPECTER

SPECTER started as a little personal project, I just wanted to see what the 2.4GHz band looked like on a cheap NRF24L01 module and a Pico W. Then I added a menu. Then settings. Then OTA updates, a screensaver, a buzzer, battery monitoring and an easter egg. At some point I looked at it and thought "this is kind of a whole OS now" and figured, why not just open source it? So here we are.

It runs completely custom MicroPython firmware, no pre-built apps or libraries beyond the ssd1306 driver. The hardware is hand soldered on a 60x80mm perfboard and fits in your hand. Honestly if you are building one yourself I would go with a bigger board. 60x80mm is extremely compact and I had to use a slimmer 803160 1800mAh LiPo specifically because my usual 104050 cells are too wide and just would not fit. A bigger perfboard gives you way more headroom to work with and makes the whole build much less of a puzzle. The 60x80mm works but it is definitely not what you would call spacious haha.

Built by [Phillip Rødseth](https://kjern.no) / Kjern.no. Open source under CERN-OHL-W-2.0.

---

## What it actually does

There are 7 screens you can navigate between using the buttons. Here is what each one does and why it is useful:

**2.4G SPECTRUM**
This is the main attraction. The NRF24L01 scans every channel in the 2.4GHz band (2402-2480MHz) and draws a live bar graph across the full 128px width of the OLED. Each bar jumps up instantly when a signal is detected and falls off smoothly. There are peak markers that float above the bars and fall much slower so you can see where the action was even after it has moved on. WiFi shows up as wide solid blocks (it occupies about 20 channels at once), Bluetooth shows up as short spikes jumping around because it hops 1600 times per second. You can even hold it up against a running microwave and watch the higher frequencies light up as one big thick bar across the display, which is pretty fun :)

**WIFI SCANNER**
Uses the Pico W built in WiFi chip to scan for nearby networks. Lists them sorted by signal strength (strongest first) with SSID, dBm and channel. Scrollable with a scrollbar on the right edge.

**BT MONITOR**
Bluetooth Low Energy devices advertise themselves on three fixed channels (37, 38, 39) before they connect to anything. This screen watches all three simultaneously and shows live bar charts of activity per channel with peak markers. Good for seeing how many BLE devices are nearby.

**HOP COUNTER**
Counts how many times BLE devices switch between advertising channels per second, and plots that as a scrolling 20 second bar graph. More hops generally means more devices. Just a fun way to see the radio environment change as people walk in and out of range.

**SIGNAL METER**
A single big horizontal bar that shows signal strength on one specific channel. Use UP/DOWN to tune the channel up or down. Point the antenna at something and watch the bar react as you move closer or further away. Feels a bit like a metal detector but for radio signals. Also useful for finding which WiFi channel is least congested.

**STATS**
7 pages of real hardware stats. All of it is read from actual hardware, nothing is hardcoded or estimated. Battery voltage and percentage, CPU frequency, chip temperature from the internal sensor, RAM usage, flash usage, NRF status register, WiFi MAC address, unique chip ID, boot count and button press count this session. UP/DOWN scrolls between pages.

**SETTINGS**
Brightness, scan speed, bar decay rate, peak decay rate, battery update interval, buzzer on/off, WiFi setup and OTA firmware updates. WiFi setup has a full on-screen keyboard you can type into using the buttons. The error log viewer is also in here under "Error Log" which shows anything that crashed and got logged to flash.

---

## Hardware

You need these parts to build one:

| Part | Notes |
|------|-------|
| Raspberry Pi Pico W | the brain, has built in WiFi which we use for the wifi scanner and OTA updates |
| NRF24L01+PA+LNA | the radio module, the PA+LNA version has an external antenna and is much more sensitive than the plain version |
| SSD1306 0.96" OLED | 128x64 pixels, I2C, the most common cheap OLED module around |
| 3.7V LiPo battery | single cell only, 1800-2500mAh works well |
| TP4056 charging module | handles charging safely, do not skip this |
| 5x tactile push switches | standard 6x6mm THT buttons |
| Passive piezo buzzer | needs PWM to make sound, the code drives it at 2500Hz which is a good middle ground for most passive buzzers |
| 10µF capacitor | not strictly necessary, but if your NRF acts weird when the radio activates (init failures, corrupted reads) it is usually just a voltage dip when the radio draws a burst of current. if you see this, solder a 10µF as close to the VCC and GND pins as you can and it will fix it :) |
| 2x 100kΩ resistors | voltage divider for the battery ADC sense |

For full wiring, see **[hardware/WIRING.md](hardware/WIRING.md)**. Read that before touching anything, especially the battery section. The schematic is in **[hardware/SCHEMATICS.pdf](hardware/SCHEMATICS.pdf)** if you want a technical view but WIRING.md is much easier to follow for actually building it.

> Seriously read the battery section in WIRING.md before connecting power. The voltage divider is not optional and wiring it wrong will permanently damage the ADC pin on your Pico.

---

## Installing

### The easy way, UF2 drag and drop

This is the recommended way for a first install. You do not need MicroPython installed already, the UF2 contains everything.

1. Hold **BOOTSEL** on the Pico W while plugging it into USB
2. It shows up on your computer as a USB drive called **RPI-RP2**
3. Go to [Releases](https://github.com/KjernNo/specter/releases) and download the latest **`specter-vX.X.X.uf2`**
4. Drag the UF2 file onto the RPI-RP2 drive
5. The drive disappears and the Pico reboots, SPECTER starts up

That's it. Took maybe 30 seconds.

### If SPECTER is already installed, OTA update

Go to **Settings → Check Updates** on the device. It connects to your WiFi, checks specter.kjern.no for a newer version and installs it if one is available. WiFi needs to be set up first under **Settings → WiFi Setup** where you can pick your network and type the password using the on-screen keyboard.

### Manual install, for developers

1. Flash standard MicroPython for Pico W from [micropython.org](https://micropython.org/download/RPI_PICO_W/)
2. Download the latest **`specter-firmware-vX.X.X.zip`** from [Releases](https://github.com/KjernNo/specter/releases) and extract it
3. Copy everything to the Pico keeping the folder structure exactly as it is in the zip
4. Reset and SPECTER boots

---

## Button layout

```
[ UP  ] [ DN  ] [ SEL ] [ BCK ] [ PWR ]
  GP2     GP3     GP4     GP5     GP6
```

| Button | What it does |
|--------|-------------|
| UP | scroll up, increase a value |
| DOWN | scroll down, decrease a value |
| SELECT | open a screen, confirm something. hold 3 seconds on the menu for a surprise :) |
| BACK | exit the current screen, go back to menu, delete a character in the keyboard |
| POWER | hold 2 seconds to shut down (shows a countdown), single press to wake back up |

All buttons are wired to GND with internal pull-downs, so press = HIGH.

---

## Folder structure

```
main.py                         boots everything, runs the menu loop
VERSION                         version number, read on boot and saved to settings
core/
  hw.py                         every hardware pin definition lives here
  boot.py                       the boot screen (SPECTER / by Kjern)
  buttons.py                    debounced button reading, beeps on every press
  nrf.py                        bare metal NRF24L01 driver, RX and carrier detect only
  battery.py                    reads LiPo voltage via 100k+100k divider on GP28
  power.py                      GP6 power button, 2s hold to shut down, lightsleep wake
  buzzer.py                     PWM piezo driver at 2500Hz
  storage.py                    reads and writes JSON files to flash
  OLED/
    screensaver.py              bouncing SPECTER logo after 30s of no button presses
  error-handling/
    logger.py                   logs errors to /data/specter_log.txt (max 30 lines)
  languages/
    lang.py                     loads strings.json and returns T("key") for any screen
    strings.json                every UI string in English and Norwegian Bokmal
screens/
  screen_spectrum.py            2.4GHz live spectrum analyzer
  screen_wifi.py                WiFi network scanner
  screen_bt.py                  BLE advertising channel monitor
  screen_hop_counter.py         BLE channel hop rate counter
  screen_signal_meter.py        single channel signal strength meter
  screen_stats.py               7 pages of system stats
  screen_settings.py            settings, WiFi setup, OTA, error log
  screen_wifi_setup.py          WiFi network picker with on-screen keyboard
  screen_ota.py                 OTA firmware updater
  screen_log.py                 error log viewer
modules/
  ssd1306.py                    SSD1306 OLED driver
hardware/
  SCHEMATICS.pdf                schematic PDF export
  SPECTER.kicad_sch             KiCad schematic source
  WIRING.md                     plain language wiring guide, start here
data/                           created automatically on first boot
  specter_data.json             boot count and battery cycles
  specter_settings.json         all user settings
  specter_log.txt               error log
```

---

## OTA updates

SPECTER has a full over the air update system. When a new version is released on GitHub, the CI/CD pipeline notifies specter.kjern.no which fetches the release info from GitHub. Devices can then check for and install updates through the settings menu.

The update downloads the firmware zip directly to flash in small chunks (never buffered in RAM) then extracts it file by file, also straight from flash. This way memory is never a bottleneck even on a Pico W with everything already loaded.

After a successful install the device saves the new version number to settings and reboots into the fresh firmware.

---

## Contributing

Pull requests are very welcome! A few things to know before diving in:

Comments should explain the *why* behind decisions, not just describe what the line does. If you are adding a new feature, explain why you made the choices you did.

All UI text goes in `core/languages/strings.json`, never hardcoded in a screen file. For the English entry just write the string normally. For Norwegian just put "xxx" as a placeholder if you don't know the translation, or if you happen to be Norwegian yourself feel free to add the proper translation, it really helps when someone eventually gets the Norwegian font working (the ssd1306 font is ASCII only right now so å, ø and æ can not be displayed, but the groundwork is all there) :)

New screens go in `screens/` and need a `run(oled)` function. Add the screen to `MENU()` in `main.py` and add the menu label key to `strings.json`.

### Commit message keywords

These control what the CI/CD pipeline does with the release version:

| Keyword in commit message | Effect |
|--------------------------|--------|
| `[major]` | 1.2.3 becomes 2.0.0 |
| `[minor]` | 1.2.3 becomes 1.3.0 |
| nothing | 1.2.3 becomes 1.2.4 |
| `[NO-NEW]` | version stays the same, existing release files are replaced |

Keywords are case insensitive and can go anywhere in the commit message.

---

## License

CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

Full text in [LICENSE](LICENSE), attribution requirements in [NOTICE.md](NOTICE.md).

Short version: use it, modify it, sell products based on it. Just keep the source open, credit Kjern.no, and if your product has a display it must show "SPECTER, by Kjern" or equivalent on the boot screen. The credit cannot imply that Kjern.no endorses or is affiliated with your product, it is credit only.

---

*Kjern, kjern.no*
