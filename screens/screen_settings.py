# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_settings.py, lets the user configure all specter settings
# navigation works like this:
#   up/down to move between settings
#   select to start editing the highlighted setting
#   while editing, up/down changes the value
#   select confirms and saves, back cancels the change
#   back from the main list saves and exits
#
# some settings are "action" items rather than numeric values
# these have min=-1 which we use as a flag to launch another screen
# wifi setup opens screen_wifi_setup, check updates opens screen_ota
# importing those screens here would slow down startup so we import them
# lazily inside the select handler only when actually needed
#
# language is a special case because its a string toggle (en/no) not a number
# buzzer_on is also special because its a binary 0/1 displayed as on/off
# the _val_display function handles formatting these for the screen

import utime
import storage
import buttons
import power
import buzzer
from lang import T

# settings definition list
# each entry is (language key for label, storage key, min value, max value, step size)
# min=-1 means its an action item that launches another screen instead of editing a value
SETTINGS = [
    ("set_brightness",  "brightness",  10,  255, 10),   # oled contrast
    ("set_scan_speed",  "scan_speed",  50,  1000, 50),  # us per channel in spectrum
    ("set_decay",       "decay",       50,  99,  1),    # bar decay rate
    ("set_peak_decay",  "peak_decay",  80,  99,  1),    # peak marker decay rate
    ("set_batt_update", "batt_update", 5,   60,  5),    # battery refresh interval seconds
    ("set_buzzer",      "buzzer_on",   0,   1,   1),    # buzzer on or off
    # language selection is disabled for now -- norwegian special characters
    # (å, ø, æ) cannot be displayed on the ssd1306 ascii font, working on a fix
    # ("set_language", "language", 0, 1, 1),
    ("set_wifi",        "wifi_ssid",  -1,  -1,  -1),   # action, opens wifi setup screen
    ("set_updates",     "ota",        -1,  -1,  -1),   # action, opens ota screen
    ("set_log",         "log",        -1,  -1,  -1),   # action, opens error log screen
]

def _val_display(key, val):
    # formats the current value of a setting for display on the oled
    # special cases for non-numeric settings
    if key == "language":
        return "NO" if val == 'no' else "EN"
    if key == "buzzer_on":
        return "PA" if val == 1 else "AV"   # pa = on in norwegian, av = off
    if key == "wifi_ssid":
        ssid = storage.get_setting('wifi_ssid')
        return ssid[:8] if ssid else "---"   # show saved ssid or dashes if none
    if key == "ota":
        return ">>>"   # visual indicator that this is an action item
    return str(val)

def run(oled):
    settings = storage.get_settings()
    sel      = 0       # currently highlighted setting index
    editing  = False   # whether we are in edit mode for the selected setting
    redraw   = True

    while True:
        if power.check(0):
            return

        if redraw:
            oled.fill(0)
            oled.text(T("set_title")[:16], 0, 0)
            oled.hline(0, 9, 128, 1)

            # show 4 settings at a time, scroll as needed
            start = max(0, min(sel, len(SETTINGS) - 4))
            for i, (lkey, skey, mn, mx, step) in enumerate(SETTINGS[start:start+4]):
                actual = start + i
                y      = 12 + i * 12
                val    = settings.get(skey, storage.SETTINGS_DEFAULTS.get(skey, ''))
                name   = T(lkey)[:9]
                disp   = _val_display(skey, val)
                line   = name + " " + disp

                if actual == sel:
                    oled.fill_rect(0, y - 1, 128, 11, 1)
                    if editing:
                        # show angle brackets around the line to indicate edit mode
                        oled.text("<" + line[:13] + ">", 0, y, 0)
                    else:
                        oled.text(">" + line[:14], 0, y, 0)
                else:
                    oled.text(" " + line[:15], 0, y, 1)

            oled.hline(0, 54, 128, 1)
            # hint text changes depending on whether we are navigating or editing
            if editing:
                oled.text(T("set_hint_edit")[:16], 0, 56)
            else:
                oled.text(T("set_hint_nav")[:16], 0, 56)
            oled.show()
            redraw = False

        if not editing:
            # navigation mode
            if buttons.up():
                sel    = max(0, sel - 1)
                redraw = True
            if buttons.down():
                sel    = min(len(SETTINGS) - 1, sel + 1)
                redraw = True
            if buttons.select():
                lkey, skey, mn, mx, step = SETTINGS[sel]
                if mn == -1:
                    # action item, import and run the appropriate screen
                    if skey == 'wifi_ssid':
                        import screen_wifi_setup
                        screen_wifi_setup.run(oled)
                    elif skey == 'ota':
                        import screen_ota
                        screen_ota.run(oled)
                    elif skey == 'log':
                        import screen_log
                        screen_log.run(oled)
                    redraw = True
                else:
                    editing = True
                    redraw  = True
            if buttons.back():
                # save settings and exit
                storage.save_settings(settings)
                return
        else:
            # edit mode, up/down changes the value, select saves, back cancels
            lkey, skey, mn, mx, step = SETTINGS[sel]
            cur = settings.get(skey, storage.SETTINGS_DEFAULTS.get(skey, mn))

            if buttons.up():
                if skey == 'language':
                    # toggle between en and no
                    settings[skey] = 'no' if cur == 'en' else 'en'
                else:
                    settings[skey] = min(mx, cur + step)
                storage.save_settings(settings)   # save immediately on each change
                redraw = True

            if buttons.down():
                if skey == 'language':
                    settings[skey] = 'en' if cur == 'no' else 'no'
                else:
                    settings[skey] = max(mn, cur - step)
                storage.save_settings(settings)
                redraw = True

            if buttons.select():
                # confirm and exit edit mode
                editing = False
                storage.save_settings(settings)
                redraw  = True

            if buttons.back():
                # cancel edit, reload settings to discard the change on this item
                editing  = False
                settings = storage.get_settings()
                redraw   = True

        utime.sleep_ms(20)