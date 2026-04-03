# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# power.py, handles the gp6 power button for shutdown and wake
#
# call power.check() every loop iteration from any screen and it just works
# no need to wire it into each screen individually for the shutdown logic,
# though screens do need to import it and call check() to get the behaviour
#
# shutdown flow:
#   hold gp6 for 2 seconds -> countdown shown -> goodbye screen -> blank
#   -> lightsleep loop (basically off, just watching gp6)
#   -> single press on gp6 -> main() called directly -> boot screen -> menu
#
# why call main() instead of machine.reset()?
# reset() kills the usb connection and thonny throws a fit about it
# calling main() directly keeps usb alive which is much nicer for development
# on a finished product you could swap to reset() if you wanted a cleaner boot
#
# BOOT_GRACE_MS exists because if you hold gp6 to wake up and dont release
# fast enough, the device would immediately start the shutdown countdown again
# the grace period ignores the power button for 1.5 seconds after boot
# so you have time to lift your finger without immediately shutting back down
#
# current draw estimates (rough! not measured yet, just educated guesses):
#   active (menu running, oled on, nrf idle):  ~50-70mA probably
#   lightsleep "off" (oled blank, cpu halted): ~2-5mA probably
#   these are ballpark figures based on datasheets, actual draw
#   may differ, measure it yourself before putting it on a spec sheet :)
#
# the lightsleep() call is the key to low power shutdown
# it halts the cpu and most peripherals while keeping ram intact
# we sleep in 50ms chunks so a button press is never missed
# 50ms = checking 20 times per second, plenty responsive

from machine import Pin, lightsleep
import utime
import storage
from lang import T

_pwr       = Pin(6, Pin.IN, Pin.PULL_DOWN)   # power button, press = HIGH
_oled      = None    # oled reference set by init()
_boot_time = 0       # set fresh each time main() runs
_main_fn   = None    # reference to main() for direct wake call

PWR_HOLD   = 2000    # hold this many ms before shutdown triggers
BOOT_GRACE = 1500    # ignore power button for this long after boot

def init(oled, boot_time=0, main_fn=None):
    # call this at the very start of main() every time it runs
    # needs the oled to draw the countdown and goodbye screen
    # needs main_fn so the wake loop can restart the os without a hardware reset
    # needs boot_time so the grace period works correctly after wake
    global _oled, _boot_time, _main_fn
    _oled      = oled
    _boot_time = boot_time
    _main_fn   = main_fn

def _shutdown():
    # show goodbye, blank the screen, then enter the low power wake loop
    # once in here we dont come back until gp6 is pressed
    _oled.fill(0)
    _oled.text(T("menu_title"),  36, 20)
    _oled.text(T("pwr_goodbye"), 32, 34)
    _oled.show()
    utime.sleep_ms(1000)
    _oled.fill(0)
    _oled.show()

    # wait for the button to be fully released before sleeping
    # otherwise the release edge would immediately wake us back up, which is annoying
    while _pwr.value() == 1:
        utime.sleep_ms(10)
    utime.sleep_ms(100)   # extra debounce just to be safe

    # low power wake loop
    # lightsleep(50) halts the cpu for 50ms then we check gp6
    # cpu is actually doing nothing during those 50ms, not spinning
    # this is what keeps current draw low while the device is "off"
    while True:
        lightsleep(50)
        if _pwr.value() == 1:
            utime.sleep_ms(50)   # debounce the wake press
            if _pwr.value() == 1:
                # legit press, wait for release then restart
                while _pwr.value() == 1:
                    utime.sleep_ms(10)
                utime.sleep_ms(50)
                if _main_fn:
                    _main_fn()
                return False

def check(boot_time=None):
    # call this every loop iteration from any screen
    # returns True if gp6 was tapped briefly (caller should redraw)
    # returns False normally
    # never returns if shutdown completes, main() gets called directly from _shutdown()
    global _boot_time
    bt = boot_time if boot_time is not None else _boot_time

    # grace period after boot, ignore the button entirely during this window
    if utime.ticks_diff(utime.ticks_ms(), bt) < BOOT_GRACE:
        return False

    if _pwr.value() != 1:
        return False   # not pressed, nothing to do

    t = utime.ticks_ms()

    while True:
        held = utime.ticks_diff(utime.ticks_ms(), t)

        if _pwr.value() == 0:
            # released before threshold, just a tap, tell caller to redraw
            _oled.fill(0)
            return True

        if held > 500:
            # show the countdown after 500ms so quick taps dont flash the screen
            # below 500ms the screen stays as-is so it feels instant
            _oled.fill(0)
            _oled.text(T("pwr_hold"), 8, 18)
            _oled.text(T("pwr_off"),  40, 30)
            secs_left = max(0.0, round((PWR_HOLD - held) / 1000.0, 1))
            _oled.text(str(secs_left) + "s", 52, 42)
            _oled.show()

        if held >= PWR_HOLD:
            # held long enough, play the shutdown beep and shut down
            try:
                import buzzer
                buzzer.long_beep(400)
            except:
                pass   # if buzzer fails for any reason, just carry on and shut down anyway
            _shutdown()
            return False

        utime.sleep_ms(20)