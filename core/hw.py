# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# hw.py, hardware definitions and object creation for SPECTER
# everything that touches physical pins lives here
# other files import from here instead of creating their own pin objects
# that way if you ever change a pin, you only change it in one place
# and nothing else breaks

# IMPORTANT: hw.py is also where the sys.path setup happens
# it gets imported early in main.py before other imports, so all the path
# appending for /core /modules /screens is done here
# if you move hw.py or rename it, make sure the path setup moves with it

import sys

# tell micropython where to look for our module folders
# without this, imports like "import buttons" would fail because
# micropython only searches the root and /lib by default
sys.path.append('/core')
sys.path.append('/core/languages')
sys.path.append('/modules')
sys.path.append('/screens')

from machine import Pin, SPI, I2C
import ssd1306

# oled display, i2c on gp0 (sda) and gp1 (scl)
# 128x64 pixels, address 0x3c (standard for most ssd1306 modules)
# 400khz works reliably here, tried 1mhz and got EIO errors on this module
# if you get ETIMEDOUT or EIO errors, try dropping freq to 100000 first
i2c  = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# nrf24l01 radio module on spi1
# sck=gp10, mosi=gp11, miso=gp12, csn=gp14, ce=gp17
# 4mhz baudrate is safe and stable, the nrf can technically do 10mhz
# but 4mhz avoids any timing issues on longer wires
# csn is chip select (active low), ce is chip enable (controls rx/tx state)
spi = SPI(1, baudrate=4000000, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
csn = Pin(14, Pin.OUT)
ce  = Pin(17, Pin.OUT)

# navigation buttons, all wired with pull_down resistors
# press = pin goes HIGH (value returns 1)
# up and down scroll through menus
# select confirms / enters a screen
# back exits the current screen and returns to menu
btn_up  = Pin(2, Pin.IN, Pin.PULL_DOWN)
btn_dn  = Pin(3, Pin.IN, Pin.PULL_DOWN)
btn_sel = Pin(4, Pin.IN, Pin.PULL_DOWN)
btn_bk  = Pin(5, Pin.IN, Pin.PULL_DOWN)