# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# boot.py, draws the boot screen when SPECTER starts up
# kept intentionally simple, just the name and credit, clean and minimal
#
# if you fork this firmware and use it in your own product, you are required
# by NOTICE.md to keep "SPECTER" and "by Kjern" (or equivalent wording)
# visible on the boot screen, you can add your own branding around it
# but you cannot remove or hide this text, see NOTICE.md for the full rules

import utime
from lang import T

def draw_boot(oled):
    # play startup sound first if the buzzer is enabled
    # wrapped in try/except so if buzzer.py isnt loaded yet it just skips
    try:
        import buzzer
        buzzer.startup()
    except:
        pass

    oled.fill(0)

    # "SPECTER" centered horizontally, 7 chars x 8px = 56px wide, so x=36 centers it
    oled.text(T("menu_title"), 36, 24, 1)

    # "by Kjern" just below, 8 chars x 8px = 64px wide, so x=32 centers it
    oled.text(T("boot_by"), 32, 36, 1)

    oled.show()
    utime.sleep_ms(1500)   # hold the screen for 1.5 seconds before the os loads

    # clear screen and brief pause before menu appears
    oled.fill(0)
    oled.show()
    utime.sleep_ms(150)