# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_hop_counter.py, BLE channel hop counter
# bluetooth low energy devices hop between the three advertising channels
# (ch37=2402mhz, ch38=2426mhz, ch39=2480mhz) when broadcasting their presence
# this screen counts how many channel hops per second are detected
# and shows a scrolling bar graph of hop rate over the last 20 seconds
#
# a hop is counted when activity is detected on a different channel than last time
# this filters out counting the same burst multiple times on the same channel
# a single device advertises roughly every 20-200ms depending on its settings
# in a busy area with lots of bluetooth devices you can see 20-50+ hops per second
#
# the graph scrolls left as time passes, newest data always on the right
# peak rate is tracked since the screen was opened
# total hops is a running count of all detected transitions

import utime
import nrf
import buttons
import power

# ble advertising channels mapped to nrf channel numbers
# these are the only three channels ble uses for advertising/discovery
BLE_CH = {37: 2, 38: 26, 39: 80}

DISP_W      = 128
HISTORY_LEN = 20   # seconds of history shown in the graph
GRAPH_H     = 30   # pixel height of the graph area
GRAPH_Y     = 12   # y pixel of the top of the graph
BAR_W       = DISP_W // HISTORY_LEN   # width of each bar in pixels

def run(oled):
    history          = [0] * HISTORY_LEN   # one count per second, oldest left newest right
    hops_this_second = 0
    last_tick        = utime.ticks_ms()
    total_hops       = 0
    peak_rate        = 0
    last_ch          = -1   # last channel activity was seen on, used to detect hops
    redraw           = True

    while True:
        if power.check(0):
            return
        if buttons.back():
            return

        # scan all three advertising channels as fast as possible
        for ble, nrf_ch in BLE_CH.items():
            if nrf.scan_channel(nrf_ch):
                # only count as a hop if this is a different channel than the last hit
                # prevents counting multiple detections on the same channel as separate hops
                if ble != last_ch:
                    hops_this_second += 1
                    total_hops       += 1
                    last_ch           = ble

        # once per second, commit the current count to history and reset
        if utime.ticks_diff(utime.ticks_ms(), last_tick) >= 1000:
            history.pop(0)           # drop oldest entry
            history.append(hops_this_second)
            if hops_this_second > peak_rate:
                peak_rate = hops_this_second
            hops_this_second = 0
            last_tick        = utime.ticks_ms()
            redraw           = True

        if redraw:
            oled.fill(0)
            oled.text("HOP COUNTER", 20, 0)
            oled.hline(0, 9, 128, 1)

            # scale bars relative to the highest value in history
            max_val = max(max(history), 1)

            for i, val in enumerate(history):
                h = int(val * GRAPH_H / max_val)
                if h > 0:
                    x = i * BAR_W
                    oled.fill_rect(x, GRAPH_Y + (GRAPH_H - h), BAR_W - 1, h, 1)

            oled.hline(0, GRAPH_Y + GRAPH_H, 128, 1)

            # current rate and peak below graph
            oled.text("Now:" + str(history[-1]) + "/s", 0,  46)
            oled.text("Pk:"  + str(peak_rate),          72, 46)
            oled.hline(0, 54, 128, 1)
            oled.text("Tot:" + str(total_hops % 100000), 0, 56)
            oled.text("BK=back", 80, 56)
            oled.show()
            redraw = False

        utime.sleep_ms(10)