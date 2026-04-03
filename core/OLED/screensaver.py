# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screensaver.py, bouncing SPECTER logo screensaver
# activates after TIMEOUT_MS of no button presses on the main menu
# works exactly like a DVD player screensaver, logo bounces around the screen
# any button press or power button tap wakes it back up immediately
#
# the bounce logic works by tracking an x,y position and a direction vector (dx, dy)
# each frame we move the position by dx, dy
# when the text would go off the edge we flip the relevant direction component
# this gives the classic bouncing effect
#
# we dim the display slightly while the screensaver is running to save oled life
# and restore it when waking up

import utime
from machine import Pin
from lang import T
import storage

TIMEOUT_MS = 30000   # 10 seconds for testing, change to 30000 for release
_last_activity = utime.ticks_ms()   # tracks when the last button press happened

# text dimensions on ssd1306, each char is 8x8px
# "SPECTER" = 7 chars = 56px wide, 8px tall
TEXT_W = 56
TEXT_H = 8
DISP_W = 128
DISP_H = 64

def poke():
    # call this every time a button is pressed anywhere in the main menu loop
    # resets the inactivity timer so the screensaver doesnt activate
    global _last_activity
    _last_activity = utime.ticks_ms()

def should_activate():
    # returns True if enough time has passed since the last button press
    return utime.ticks_diff(utime.ticks_ms(), _last_activity) > TIMEOUT_MS

def run(oled):
    # runs the bouncing screensaver until any button is pressed
    # imports buttons here to avoid circular imports at module level
    from hw import btn_up, btn_dn, btn_sel, btn_bk
    pwr = Pin(6, Pin.IN, Pin.PULL_DOWN)

    # dim the display a bit while screensaver runs, better for oled longevity
    saved_brightness = storage.get_setting('brightness')
    oled.contrast(max(10, saved_brightness // 4))

    # starting position, roughly centered
    x  = (DISP_W - TEXT_W) // 2
    y  = (DISP_H - TEXT_H) // 2
    dx = 1    # horizontal direction, 1 = right, -1 = left
    dy = 1    # vertical direction, 1 = down, -1 = up

    frame = 0

    while True:
        # wake up on any button press
        if (btn_up.value() == 1 or btn_dn.value() == 1 or
            btn_sel.value() == 1 or btn_bk.value() == 1 or
            pwr.value() == 1):
            break

        # update position
        x += dx
        y += dy

        # bounce off edges
        if x <= 0 or x >= DISP_W - TEXT_W:
            dx = -dx
            x  = max(0, min(x, DISP_W - TEXT_W))

        if y <= 0 or y >= DISP_H - TEXT_H:
            dy = -dy
            y  = max(0, min(y, DISP_H - TEXT_H))

        # draw every 2 frames to keep it smooth without hammering the i2c bus
        if frame % 2 == 0:
            oled.fill(0)
            oled.text("SPECTER", x, y, 1)
            oled.show()

        frame += 1
        utime.sleep_ms(30)   # ~33fps movement speed, feels natural

    # restore brightness and reset activity timer on wake
    oled.contrast(saved_brightness)
    poke()