# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# buttons.py, debounced button reading for all 4 navigation buttons
# buttons are wired with pull_down resistors so pressing one pulls the pin HIGH
# without debounce a single physical press can register 5-10 times because
# the mechanical contacts bounce rapidly as they close, this fixes that

# the buzzer import is done lazily (inside the function on first use) rather
# than at the top of the file, this avoids a circular import problem where
# buzzer imports storage which imports something that imports buttons and so on

import utime
from hw import btn_up, btn_dn, btn_sel, btn_bk

# 200ms felt natural after testing, fast enough to scroll quickly
# but slow enough that a single press never registers twice
DEBOUNCE_MS = 200

# tracks when each button was last successfully pressed
# used to enforce the debounce window
_last = {"up": 0, "dn": 0, "sel": 0, "bk": 0}

# total button presses this session, just for fun :)
# "if it can be counted, it shall be counted." - Phillip Rødseth, 3rd April 2026
press_count = 0

_buzzer = None   # cached buzzer module reference, loaded once on first press

def _get_buzzer():
    # load the buzzer module the first time a button is pressed
    # if it fails for any reason we just skip the sound, not a big deal
    global _buzzer
    if _buzzer is None:
        try:
            import buzzer
            _buzzer = buzzer
        except:
            pass
    return _buzzer

def _pressed(pin, name):
    # checks if a pin is currently high AND enough time has passed since the last press
    # if both are true, play the click sound and return True
    if pin.value() == 1:
        now = utime.ticks_ms()
        if utime.ticks_diff(now, _last[name]) > DEBOUNCE_MS:
            _last[name] = now
            global press_count
            press_count += 1   # increment total press counter for stats screen
            buz = _get_buzzer()
            if buz:
                buz.beep(25)   # short 25ms click sound on every button press
            return True
    return False

# these four functions are what all screens call, nice and simple
def up():     return _pressed(btn_up,  "up")
def down():   return _pressed(btn_dn,  "dn")
def select(): return _pressed(btn_sel, "sel")
def back():   return _pressed(btn_bk,  "bk")