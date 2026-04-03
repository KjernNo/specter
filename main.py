# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# main.py, the entry point for the whole OS
# this file boots everything up, sets up hardware, and runs the main menu loop
# all the actual screen logic lives in the screens/ folder
# all hardware objects are created in hw.py so everything shares the same instances
# the folder structure is:
#   core/                   hardware drivers, power, buttons, battery, lang, storage, buzzer
#   core/languages/         translation files (strings.json)
#   core/OLED/              oled related modules like the screensaver
#   core/error-handling/    error logging and crash handling
#   modules/                third party stuff like ssd1306
#   screens/                one file per screen, each has a run(oled) function
#   data/                   json files for settings and persistent data (created on first boot)

import sys

# we need to tell micropython where our folders are before importing anything
# otherwise it only looks in the root and /lib and wont find our files
sys.path.append('/core')
sys.path.append('/core/languages')
sys.path.append('/core/OLED')
sys.path.append('/core/error-handling')
sys.path.append('/modules')
sys.path.append('/screens')

import utime
from machine import Pin, reset

# boot time is captured here as early as possible, before any imports
# this is important because power.py uses it to calculate uptime accurately
# if we captured it later, the time spent importing modules would be missing
_boot_time = utime.ticks_ms()

# now we can import everything else since the paths are set up
import nrf              # nrf24l01 driver, handles all the radio stuff
import boot             # draws the boot screen with SPECTER branding
import buttons          # debounced button reading for all 4 nav buttons
import battery          # reads battery voltage from gp28 via voltage divider
import storage          # reads and writes settings and data to flash as json
import power            # handles the gp6 power button, shutdown and wake
import buzzer           # piezo buzzer feedback on gp18
import screensaver      # bouncing SPECTER logo, activates after 30s of inactivity
import logger           # error logger, writes to /data/specter_log.txt
import screen_spectrum  # 2.4ghz live spectrum analyzer with bar graph
import screen_wifi      # scans and lists nearby wifi networks
import screen_bt        # monitors ble advertising channels 37, 38, 39
import screen_stats     # shows system stats across 7 scrollable pages
import screen_settings  # lets user change settings, set up wifi, check for updates
import screen_wifi_setup # wifi network picker and on-screen keyboard for password
import screen_ota          # checks specter.kjern.no for firmware updates and installs them
import screen_hop_counter  # ble channel hop rate counter with scrolling graph
import screen_signal_meter # live signal strength meter, tunable by channel
import screen_log          # error log viewer in settings
from hw import oled     # the actual oled display object, shared across everything
from lang import T      # T("key") returns the right string for the current language

# apply the saved brightness setting right away before we draw anything
# if we dont do this here the screen might look different before and after settings load
oled.contrast(storage.get_setting('brightness'))

# -- menu -------------------------------------------------------------

def MENU():
    # the menu is a function rather than a list constant for a good reason,
    # if the user changes language in settings we want the labels to update
    # immediately when they return to the menu without needing a reboot
    # each entry is (display label, function to call when selected)
    return [
        (T("menu_spectrum"), screen_spectrum.run),
        (T("menu_wifi"),     screen_wifi.run),
        (T("menu_bt"),       screen_bt.run),
        (T("menu_hop"),      screen_hop_counter.run),
        (T("menu_signal"),   screen_signal_meter.run),
        (T("menu_stats"),    screen_stats.run),
        (T("menu_settings"), screen_settings.run),
    ]

def draw_menu(sel, batt_pct):
    # draws the main menu on the oled
    # sel is the currently highlighted item index
    # batt_pct is shown in the top right corner so you always know battery state
    oled.fill(0)

    # title on left, battery percentage on right of the header
    batt = str(batt_pct) + "%"
    oled.text(T("menu_title"), 0, 0)
    # calculate x position so the battery text is right aligned at pixel 128
    oled.text(batt, 128 - len(batt) * 8, 0)
    oled.hline(0, 9, 128, 1)   # separator line under header

    # we only show 4 items at a time because thats all that fits on 64px height
    # visible_start is the index of the first visible item
    # it scrolls down as sel goes past the 4th visible item
    menu = MENU()
    visible_start = max(0, min(sel, len(menu) - 4))
    for i, (name, _) in enumerate(menu[visible_start:visible_start + 4]):
        y      = 12 + i * 12   # each row is 12px tall
        actual = visible_start + i
        if actual == sel:
            # invert the selected row so the highlight is obvious
            oled.fill_rect(0, y - 1, 128, 11, 1)
            oled.text("> " + name, 0, y, 0)   # black text on white background
        else:
            oled.text("  " + name, 0, y, 1)   # normal white text

    oled.hline(0, 54, 128, 1)
    oled.text(T("menu_hint"), 0, 56)   # navigation hint at the bottom
    oled.show()

# -- nrf init ---------------------------------------------------------

def init_nrf():
    # tries to initialise the nrf24l01 up to 3 times
    # sometimes the module needs a moment after power on, hence the retries
    # if all 3 fail we show an error but carry on anyway
    # the spectrum and bt screens just wont work without it, but wifi and settings still will
    oled.fill(0)
    oled.text(T("menu_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("nrf_init"), 20, 28)
    oled.show()

    ok = False
    for _ in range(3):
        if nrf.init():
            ok = True
            break
        utime.sleep_ms(200)   # short wait between retries

    if not ok:
        # play error sound and show diagnostics on screen
        # we show the raw status register value because its useful for debugging
        # 0x00 or 0xFF means spi is completely dead (usually a wiring issue)
        # anything else means the nrf responded but setup failed somehow
        buzzer.error()
        s = nrf.status()
        oled.fill(0)
        oled.rect(0, 0, 128, 64, 1)   # border to make the error screen look distinct
        oled.text(T("nrf_fail"),  24, 8)
        oled.hline(8, 19, 112, 1)
        oled.text("STATUS:" + hex(s), 16, 28)
        oled.text(T("nrf_check"), 12, 40)
        oled.text(T("nrf_vcc"),    4, 52)
        oled.show()
        utime.sleep_ms(2000)   # give user time to read the error before moving on

# -- easter egg -------------------------------------------------------

def _easter_egg(oled):
    # easter egg screen, triggered by holding SELECT for 3 seconds on the main menu
    # fully intentional, clearly labelled in source, not hidden or obfuscated
    # most people never read source code so it still feels like a fun discovery :)
    # if you are reading this in the source... hi! you did it the nerd way.
    # "Why not add an easter egg to this code, I mean, It is currently easter break as im developing this" - Phillip Rødseth, 3rd april 2026

    # frame 1 -- entrance, just a border pulsing in
    for i in range(4):
        oled.fill(0)
        oled.rect(i, i, 128 - i*2, 64 - i*2, 1)
        oled.show()
        utime.sleep_ms(60)

    buzzer.startup()

    # frame 2 -- main easter egg screen
    oled.fill(0)

    # double border for "..drama.."
    oled.rect(0, 0, 128, 64, 1)
    oled.rect(2, 2, 124, 60, 1)

    # big surprise header, inverted because I thought it looked better
    oled.fill_rect(4, 4, 120, 12, 1)
    oled.text("!! YOU FOUND IT !!", 4, 5, 0)   # black text on white

    # the content
    oled.text("hi from phillip :)", 4, 20)
    oled.text("kjern.no", 36, 32)

    # felt like the right call for someone who just held a button
    # for 3 seconds on a handheld RF scanner, right..?
    oled.hline(4, 46, 120, 1)
    oled.text("go touch grass", 16, 50)

    oled.show()
    utime.sleep_ms(200)

    # frame 3 -- little buzzer celebration
    buzzer.beep(30)
    utime.sleep_ms(60)
    buzzer.beep(30)
    utime.sleep_ms(60)
    buzzer.beep(60)

    utime.sleep_ms(3000)

    # frame 4 -- fade out with shrinking border
    for i in range(4):
        oled.fill(0)
        oled.rect(i, i, 128 - i*2, 64 - i*2, 1)
        oled.show()
        utime.sleep_ms(60)

    oled.fill(0)
    oled.show()

# -- main loop --------------------------------------------------------

def main():
    # this function runs the whole os, called once on boot and again on wake from power off
    # we pass a reference to this function into power.init so power.py can call main()
    # directly when the user presses gp6 to wake up, instead of doing a hardware reset
    # doing it this way keeps thonny connected and avoids the reset causing usb issues

    # capture a fresh boot time each time main() is called
    # this matters because on wake from shutdown, main() is called directly
    # by power.py and ticks_ms() has been running the whole time the pico
    # was sitting in the wake loop, so the module level _boot_time is stale
    global _boot_time
    _boot_time = utime.ticks_ms()
    power.init(oled, _boot_time, main_fn=main)

    storage.on_boot()      # increment boot counter in flash
    boot.draw_boot(oled)   # show SPECTER boot screen
    init_nrf()             # try to start the radio

    sel       = 0
    redraw    = True
    last_batt = utime.ticks_ms()
    batt_pct  = battery.percentage()   # read battery once at startup

    while True:
        # check the power button every single loop iteration
        # returns True if it was tapped briefly (cancelled), in which case we redraw
        # if it was held for 2 seconds it shuts down and never returns from check()
        if power.check(_boot_time):
            screensaver.poke()
            redraw = True

        # check if screensaver should activate after 30s of inactivity
        if screensaver.should_activate():
            screensaver.run(oled)
            redraw = True

        # battery reading is cached in battery.py so this doesnt hit the adc every loop
        # we still only update the displayed value every 30 seconds though
        # no point redrawing the menu constantly for a percentage that barely changes
        if utime.ticks_diff(utime.ticks_ms(), last_batt) > 30000:
            batt_pct  = battery.percentage()
            last_batt = utime.ticks_ms()
            redraw    = True

        if redraw:
            draw_menu(sel, batt_pct)
            redraw = False

        menu = MENU()   # call every loop so labels are always current language

        if buttons.up():
            # wrap around so going up from the first item takes you to the last
            screensaver.poke()
            sel    = (sel - 1) % len(menu)
            redraw = True

        if buttons.down():
            # wrap around so going down from the last item takes you to the first
            screensaver.poke()
            sel    = (sel + 1) % len(menu)
            redraw = True

        # select and easter egg share the same button so we read it raw
        # if released quickly = normal select, held 3 seconds = easter egg
        # this way the two actions never conflict with each other
        if buttons.btn_sel.value() == 1:
            screensaver.poke()   # any select interaction counts as activity
            utime.sleep_ms(30)   # debounce
            if buttons.btn_sel.value() == 1:
                t = utime.ticks_ms()
                while buttons.btn_sel.value() == 1:
                    if utime.ticks_diff(utime.ticks_ms(), t) >= 3000:
                        # held 3 seconds -- easter egg!
                        while buttons.btn_sel.value() == 1:
                            utime.sleep_ms(10)
                        _easter_egg(oled)
                        redraw = True
                        break
                    utime.sleep_ms(20)
                else:
                    # released before 3 seconds -- normal select action
                    screensaver.poke()
                    buzzer.double()
                    try:
                        menu[sel][1](oled)
                    except Exception as e:
                        # something crashed in a screen, log it and show error
                        # then return to menu gracefully instead of freezing
                        err = menu[sel][0] + ": " + str(e)
                        logger.log(err)
                        buzzer.error()
                        oled.fill(0)
                        oled.rect(0, 0, 128, 64, 1)
                        oled.text("SCREEN ERROR", 12, 8)
                        oled.hline(8, 19, 112, 1)
                        oled.text(str(e)[:16], 0, 24)
                        oled.text(str(e)[16:32], 0, 34)
                        oled.text("logged to file", 8, 46)
                        oled.text("returning...", 12, 56)
                        oled.show()
                        utime.sleep_ms(3000)
                    oled.contrast(storage.get_setting('brightness'))
                    redraw = True

        utime.sleep_ms(20)   # small sleep to keep cpu usage reasonable in the menu loop

main() 
