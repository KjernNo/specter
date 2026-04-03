# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_stats.py, system stats across 7 scrollable pages
# everything here reads real values from actual hardware, nothing is faked
# up/down scrolls between pages, back exits and saves session uptime
#
# the uptime tracking works like this:
# we record when the stats screen was opened (session_start)
# every 30 seconds we save the elapsed time to flash and reset the counter
# when back is pressed we save whatever time is left
# this way we dont lose uptime if the device crashes or battery dies
# and we dont hammer the flash with writes every second either
#
# the 7 pages are:
# 1 battery,  voltage and percentage from gp28 adc
# 2 cpu,      clock frequency, internal temperature sensor, ticks
# 3 memory,   gc heap free/used/total
# 4 flash,    filesystem total/free/used via os.statvfs
# 5 hardware, nrf status register, i2c device count
# 6 network,  wifi mac address and unique chip id
# 7 history,  boot count, battery cycles, total uptime

import utime
import gc
import os
import machine
import network
import nrf
import buttons
import power
# buttons.press_count gives us the total button presses this session
import battery
import storage
from hw import i2c
from lang import T

def fmt_uptime(s):
    # converts seconds to a readable format like 1h23m45s
    return str(s//3600) + "h" + str((s%3600)//60) + "m" + str(s%60) + "s"

def get_chip_temp():
    # reads the rp2040 internal temperature sensor on adc channel 4
    # the conversion formula comes from the rp2040 datasheet section 4.9.5
    # it measures the voltage on the temperature diode and converts to celsius
    # accuracy is roughly +/- 2 degrees, good enough for a rough indication
    sensor = machine.ADC(4)
    raw    = sensor.read_u16()
    v      = raw * 3.3 / 65535
    return round(27 - (v - 0.706) / 0.001721, 1)

def get_flash_info():
    # uses os.statvfs to get filesystem usage on the pico flash
    # statvfs returns (block_size, fragment_size, total_blocks, free_blocks, ...)
    # multiplying block_size by block count gives total bytes
    try:
        s     = os.statvfs('/')
        total = s[0] * s[2] // 1024   # total kb
        free  = s[0] * s[3] // 1024   # free kb
        return total, free
    except:
        return 0, 0

def get_mac():
    # reads the wifi mac address from the pico w wireless chip
    # the mac is formatted as XX:XX:XX:XX:XX:XX
    # we activate the interface briefly just to read the mac then deactivate
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac  = wlan.config('mac')
        wlan.active(False)
        return ':'.join('{:02X}'.format(b) for b in mac)
    except:
        return "N/A"

def get_chip_id():
    # reads the unique 64 bit id burned into every rp2040 chip at the factory
    # formatted as a hex string, useful for identifying specific units
    import ubinascii
    return ubinascii.hexlify(machine.unique_id()).decode()

def run(oled):
    s           = storage.get_settings()
    batt_upd_ms = s.get('batt_update', 10) * 1000   # convert seconds to ms

    session_start = utime.ticks_ms()
    data          = storage.get()
    scroll        = 0
    NUM_PAGES     = 7
    redraw        = True
    last_save     = utime.ticks_ms()
    last_batt     = utime.ticks_ms()

    # fetch slow or static values once rather than every redraw
    # mac address and chip id dont change so no point reading them repeatedly
    mac     = get_mac()
    chip_id = get_chip_id()

    while True:
        if power.check(0):
            return
        if buttons.back():
            # save the remaining session uptime before leaving
            elapsed = utime.ticks_diff(utime.ticks_ms(), session_start) // 1000
            storage.add_uptime(elapsed)
            return

        if buttons.up():
            scroll = max(0, scroll - 1)
            redraw = True

        if buttons.down():
            scroll = min(NUM_PAGES - 1, scroll + 1)
            redraw = True

        # save uptime to flash every 30 seconds so we dont lose it on crash
        if utime.ticks_diff(utime.ticks_ms(), last_save) > 30000:
            elapsed       = utime.ticks_diff(utime.ticks_ms(), session_start) // 1000
            storage.add_uptime(elapsed)
            session_start = utime.ticks_ms()   # reset so we dont double count
            data          = storage.get()
            last_save     = utime.ticks_ms()
            redraw        = True

        # refresh battery on the interval set in settings
        if utime.ticks_diff(utime.ticks_ms(), last_batt) > batt_upd_ms:
            battery.update()
            last_batt = utime.ticks_ms()
            redraw    = True

        if redraw:
            # gather all the values we need for all pages
            gc.collect()   # run gc before reading memory so numbers are accurate
            free_kb   = gc.mem_free()  // 1024
            total_kb  = (gc.mem_free() + gc.mem_alloc()) // 1024
            alloc_kb  = gc.mem_alloc() // 1024
            nrf_ok    = nrf.status() not in (0x00, 0xFF)
            nrf_stat  = hex(nrf.status())
            i2c_devs  = i2c.scan()
            batt_pct  = battery.percentage()
            batt_v    = battery.voltage()
            session_s = utime.ticks_diff(utime.ticks_ms(), session_start) // 1000
            total_up  = data['total_uptime'] + session_s
            boots     = data['boots']
            cycles    = data['cycles']
            cpu_mhz   = machine.freq() // 1_000_000
            temp_c    = get_chip_temp()
            flash_t, flash_f = get_flash_info()
            ticks     = utime.ticks_ms()   # raw milliseconds since boot, just for fun

            # each page is a list of 4 strings, first is the page title
            # the title gets displayed inverted (black on white) as a header
            # the other 3 are data lines shown below it
            pages = [
                [T("stats_battery"),
                 T("stats_pct") + str(batt_pct) + "%",
                 "V:    " + str(batt_v) + "V",
                 battery.bar(14)],

                [T("stats_cpu"),
                 T("stats_freq") + str(cpu_mhz) + "MHz",
                 T("stats_temp") + str(temp_c) + "C",
                 T("stats_tick") + str(ticks % 1000000)],

                [T("stats_memory"),
                 T("stats_free") + str(free_kb) + "KB",
                 T("stats_used") + str(alloc_kb) + "KB",
                 T("stats_tot")  + str(total_kb) + "KB"],

                [T("stats_flash"),
                 T("stats_total") + str(flash_t) + "KB",
                 T("stats_free")  + str(flash_f) + "KB",
                 T("stats_used")  + str(flash_t - flash_f) + "KB"],

                [T("stats_hardware"),
                 T("stats_nrf")  + ("OK" if nrf_ok else "FAIL"),
                 T("stats_nrfs") + nrf_stat,
                 T("stats_i2c")  + str(len(i2c_devs)) + T("dev")],

                [T("stats_network"),
                 T("stats_mac"),
                 mac[:16],       # mac is 17 chars so it fits on one line
                 T("stats_id") + chip_id[:12]],

                [T("stats_history"),
                 T("stats_boots")   + str(boots),
                 T("stats_cycles")  + str(cycles),
                 "Presses: " + str(buttons.press_count)],
            ]

            page = pages[scroll]

            oled.fill(0)
            # header shows page number so you know where you are in the list
            oled.text(T("stats_title") + " " + str(scroll+1) + "/" + str(NUM_PAGES), 0, 0)
            oled.hline(0, 9, 128, 1)

            # page title displayed inverted as a sub-header
            oled.fill_rect(0, 11, 128, 10, 1)
            oled.text(page[0], 0, 12, 0)

            # three data lines below the title, spaced 11px apart
            for i, line in enumerate(page[1:4]):
                oled.text(line[:16], 0, 23 + i * 11)

            oled.hline(0, 54, 128, 1)
            oled.text(T("stats_hint"), 0, 56)
            oled.show()
            redraw = False

        utime.sleep_ms(100)