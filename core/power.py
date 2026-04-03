# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# power.py, handles the gp6 power button for shutdown and wake
# designed to be called from every screen loop, not just the main menu
# that way the power button works no matter what screen you are on
#
# the shutdown flow is:
#   user holds gp6 for 2 seconds -> goodbye screen -> screen goes dark
#   -> device sits in wake loop doing nothing except watching gp6
#   -> user presses gp6 -> main() is called directly -> boot screen plays
#
# we call main() directly instead of doing machine.reset() because
# reset() causes thonny to lose the usb connection and throw errors
# calling main() directly keeps the usb connection alive the whole time
# which is much nicer during development
#
# the BOOT_GRACE_MS window prevents an annoying edge case where if you
# hold gp6 to wake up and dont release fast enough, it immediately starts
# counting down for another shutdown right after booting

from machine import Pin
import utime
import storage
from lang import T

_pwr       = Pin(6, Pin.IN, Pin.PULL_DOWN)   # power button on gp6, press = HIGH
_oled      = None    # set by init(), shared oled reference from hw.py
_boot_time = 0       # timestamp of last boot, used for uptime calculation
_main_fn   = None    # reference to the main() function for direct wake call

PWR_HOLD   = 2000    # milliseconds you need to hold before shutdown triggers
BOOT_GRACE = 1500    # milliseconds after boot before power button becomes active

def init(oled, boot_time=0, main_fn=None):
    # call this at the start of main() before the menu loop begins
    # pass in the oled so we can draw on it during shutdown/countdown
    # pass in boot_time so uptime can be calculated correctly
    # pass in main_fn so we can restart the os on wake without a hardware reset
    global _oled, _boot_time, _main_fn
    _oled      = oled
    _boot_time = boot_time
    _main_fn   = main_fn

def _shutdown():
    # shows the goodbye screen then enters the wake loop
    # the wake loop does absolutely nothing except poll gp6 every 10ms
    # this is about as low power as we can get in micropython without
    # proper sleep modes (which are more complex to implement)
    _oled.fill(0)
    _oled.text(T("menu_title"),  36, 20)
    _oled.text(T("pwr_goodbye"), 32, 34)
    _oled.show()
    utime.sleep_ms(1000)
    _oled.fill(0)
    _oled.show()

    # wait for the user to finish releasing the button before entering wake loop
    # otherwise the rising edge of release would immediately trigger a wake
    while _pwr.value() == 1:
        utime.sleep_ms(10)
    utime.sleep_ms(100)   # extra debounce

    # wake loop, sits here until gp6 is pressed
    while True:
        utime.sleep_ms(10)
        if _pwr.value() == 1:
            utime.sleep_ms(50)
            if _pwr.value() == 1:
                # confirmed press, wait for release before calling main
                # this prevents the button still being held when main() starts
                # which would immediately trigger the countdown again
                while _pwr.value() == 1:
                    utime.sleep_ms(10)
                utime.sleep_ms(50)
                global _boot_time
                _boot_time = utime.ticks_ms()   # reset boot time for fresh uptime tracking
                if _main_fn:
                    _main_fn()
                return False

def check(boot_time=None):
    # call this every loop iteration from any screen or the main menu
    # returns True if button was briefly tapped and released (caller should redraw)
    # returns False if nothing happened or if boot grace period is active
    # never returns at all if shutdown completes, main() gets called directly instead
    global _boot_time
    bt = boot_time if boot_time is not None else _boot_time

    # during boot grace period the power button is completely ignored
    # this prevents accidentally shutting down right after waking up
    if utime.ticks_diff(utime.ticks_ms(), bt) < BOOT_GRACE:
        return False

    if _pwr.value() != 1:
        return False   # button not pressed, nothing to do

    t = utime.ticks_ms()   # record when the press started

    while True:
        held = utime.ticks_diff(utime.ticks_ms(), t)

        if _pwr.value() == 0:
            # button released before the 2 second threshold
            # clear the screen and tell the caller to redraw whatever was showing
            _oled.fill(0)
            return True

        if held > 500:
            # only show the countdown after 500ms so quick taps dont flash the screen
            _oled.fill(0)
            _oled.text(T("pwr_hold"), 8, 18)
            _oled.text(T("pwr_off"),  40, 30)
            secs_left = max(0.0, round((PWR_HOLD - held) / 1000.0, 1))
            _oled.text(str(secs_left) + "s", 52, 42)
            _oled.show()

        if held >= PWR_HOLD:
            # held long enough, save uptime and shut down
            # always use _boot_time from init() here, NOT bt
            # screens call check(0) which would make bt=0 and calculate
            # time since power on rather than time since this boot session started
            storage.add_uptime(
                utime.ticks_diff(utime.ticks_ms(), _boot_time) // 1000
            )
            try:
                import buzzer
                buzzer.long_beep(400)   # long beep confirms shutdown
            except:
                pass
            _shutdown()
            return False

        utime.sleep_ms(20)