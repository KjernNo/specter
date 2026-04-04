# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# buzzer.py, piezo buzzer feedback on gp18
# this is a passive piezo buzzer, the + marking is just polarity not an indicator of type
# we drive it with pwm at 2500hz instead of plain dc because pwm is louder
# tested sweep from 2000hz to 3900hz, 3900 was technically the loudest
# but 2500 sounds better and is still noticeably louder than just dc on/off
# the 10k pulldown resistor keeps the pin low when not driven

# all functions check _enabled() first so the user can turn sounds off in settings
# if buzzer_on is 0 every function just returns immediately without doing anything

from machine import Pin, PWM
import utime
import storage

_PIN = 18
FREQ = 2500   # hz, change this if you swap to a different buzzer model

def _enabled():
    # check the setting every time so changes in settings take effect immediately
    # without needing a reboot
    return storage.get_setting('buzzer_on')

def _on():
    # start the pwm signal on the buzzer pin
    # 50% duty cycle (32768 out of 65535) is standard for buzzers
    p = PWM(Pin(_PIN))
    p.freq(FREQ)
    p.duty_u16(32768)
    return p

def _off(p):
    # stop pwm and explicitly pull the pin low
    # without the explicit low, the pin can sit at a floating state
    # and the buzzer makes a faint continuous noise, not ideal
    p.deinit()
    Pin(_PIN, Pin.OUT).value(0)

def beep(ms=30):
    # short single beep, used for every button press
    # 30ms is short enough to feel like a click, not an alarm :)
    if not _enabled(): return
    p = _on(); utime.sleep_ms(ms); _off(p)

def double(ms=20):
    # two quick beeps, used when you enter a screen from the menu
    # slightly different from a single beep so you can tell them apart by sound
    if not _enabled(): return
    p = _on(); utime.sleep_ms(ms); _off(p)
    utime.sleep_ms(ms)
    p = _on(); utime.sleep_ms(ms); _off(p)

def long_beep(ms=400):
    # long single tone, used when shutting down
    # gives clear confirmation that the shutdown is happening
    if not _enabled(): return
    p = _on(); utime.sleep_ms(ms); _off(p)

def error(ms=80):
    # three rapid beeps, used for errors like nrf failing to init
    # sounds obviously wrong so you know something needs attention
    if not _enabled(): return
    for _ in range(3):
        p = _on(); utime.sleep_ms(ms); _off(p)
        utime.sleep_ms(ms)

def startup():
    # two beeps on boot, first short then longer
    # sounds like the device is waking up, nice little personality touch
    if not _enabled(): return
    p = _on(); utime.sleep_ms(60);  _off(p)
    utime.sleep_ms(40)
    p = _on(); utime.sleep_ms(120); _off(p)
