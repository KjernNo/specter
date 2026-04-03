# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# battery.py, reads lipo battery voltage and calculates percentage
# the lipo is connected through a 100k + 100k voltage divider to gp28
# the divider is needed because the pico adc only handles up to 3.3v
# and a fully charged lipo is 4.2v, which would fry the adc pin directly
# the divider halves the voltage: 4.2v becomes 2.1v, 3.0v becomes 1.5v
# both well within the safe range

# the cache system is important here, without it each screen reads
# the battery independently and you get different values on different screens
# which looks broken even if everything is working fine
# with the cache, all screens read the same value updated every 10 seconds

from machine import ADC, Pin
import utime
import storage

_adc_v = ADC(Pin(28))   # adc on gp28, reads the voltage divider midpoint

# standard single cell lipo voltage range
# below 3.0v the battery is basically empty and you risk damaging it
# above 4.2v means its fully charged
V_FULL  = 4.20
V_EMPTY = 3.00

# adc is 3.3v reference, 16 bit resolution so 65535 = 3.3v
ADC_REF = 3.3
ADC_MAX = 65535
DIVIDER = 2.0    # multiply adc reading by 2 to undo the voltage divider halving

# shared cached values, updated every CACHE_MS milliseconds
# _cache_v is voltage in volts, _cache_pct is 0.0 to 100.0
_cache_v     = 0.0
_cache_pct   = 0.0
_last_update = 0
CACHE_MS     = 10000   # 10 seconds between real adc reads

def _read_raw():
    # average 10 adc samples and convert to voltage
    # averaging reduces noise on the adc line, single samples can be jittery
    total = 0
    for _ in range(10):
        total += _adc_v.read_u16()
        utime.sleep_us(100)   # tiny gap between samples
    return (total / 10 / ADC_MAX) * ADC_REF

def update():
    # do a real adc read and update the shared cache
    # called automatically by _maybe_update() when cache is stale
    # can also be called directly if you need an immediate fresh reading
    global _cache_v, _cache_pct, _last_update
    v = _read_raw() * DIVIDER   # undo the divider to get actual battery voltage
    _cache_v   = round(v, 2)
    # clamp to 0-100 so we never show negative or over 100%
    _cache_pct = max(0.0, min(100.0, round(
        (v - V_EMPTY) / (V_FULL - V_EMPTY) * 100.0, 1
    )))
    _last_update = utime.ticks_ms()

def _maybe_update():
    # only do an adc read if the cache is older than CACHE_MS
    # this keeps cpu usage low since adc reads with averaging take a bit of time
    if utime.ticks_diff(utime.ticks_ms(), _last_update) > CACHE_MS:
        update()

def voltage():
    # returns battery voltage in volts, e.g. 3.85
    _maybe_update()
    return _cache_v

def percentage():
    # returns battery percentage 0.0 to 100.0
    _maybe_update()
    return _cache_pct

def bar(width=20):
    # returns a simple text progress bar for display on the oled
    # e.g. [============        ] for ~60%
    _maybe_update()
    filled = int(width * _cache_pct / 100)
    return "[" + "=" * filled + " " * (width - filled) + "]"