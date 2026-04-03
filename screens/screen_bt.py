# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_bt.py, bluetooth advertising channel monitor
# bluetooth low energy (ble) uses three fixed advertising channels for device discovery
# channel 37 = 2402mhz, channel 38 = 2426mhz, channel 39 = 2480mhz
# these are the channels devices use when broadcasting "i exist, come connect to me"
# things like airpods, phones with bluetooth on, keyboards, mice etc. all use these
#
# the nrf channel numbers that correspond to these ble channels are:
# ble ch37 = nrf ch2, ble ch38 = nrf ch26, ble ch39 = nrf ch80
# (nrf channel = frequency - 2400, so 2402mhz = ch2, 2426mhz = ch26, 2480mhz = ch80)
#
# we show three vertical bar charts side by side, one per advertising channel
# the bar height represents how many hits that channel has had relative to the others
# a peak line above each bar shows the historical high point, fades slowly
# if ch37 has tons of activity but ch38 and ch39 are quiet, thats unusual
# normally you see roughly equal activity across all three since devices rotate between them

import utime
import nrf
import buttons
import power
import storage
from lang import T

# the mapping from ble advertising channel numbers to nrf24l01 channel numbers
BLE_CH = {37: 2, 38: 26, 39: 80}

def run(oled):
    s       = storage.get_settings()
    scan_us = s.get('scan_speed', 200)   # microseconds to listen per channel

    # hit counters for each advertising channel, resets when you open the screen
    hits  = {37: 0, 38: 0, 39: 0}
    total = 0
    peak  = {37: 0, 38: 0, 39: 0}   # highest hit count seen for each channel

    # layout for the three bar charts
    # 3 bars x 36px wide with 4px gaps between them, 4px left margin
    BAR_W = 36
    GAP   = 4
    LEFT  = 4
    MAX_H = 36   # maximum bar height in pixels
    BAR_Y = 10   # y coordinate of the top of the bar area

    frame = 0    # frame counter used to throttle oled updates without slowing down scanning

    while True:
        if power.check(0):
            return
        if buttons.back():
            return

        # scan each of the three ble advertising channels
        for ble, nrf_ch in BLE_CH.items():
            if nrf.scan_channel(nrf_ch):
                hits[ble]  += 1
                total      += 1
                if hits[ble] > peak[ble]:
                    peak[ble] = hits[ble]   # update peak if we have a new high

        # only redraw every 3 frames to keep the scan loop running fast
        # if we redraw every single frame the oled update takes long enough
        # to noticeably slow down the scan rate
        if frame % 3 == 0:
            oled.fill(0)
            oled.text(T("bt_title"), 20, 0)
            oled.hline(0, 9, 128, 1)

            # find the highest hit count to use as the 100% reference for bar scaling
            # this way the busiest channel always reaches full height
            max_hit = max(max(hits.values()), 1)   # avoid dividing by zero

            for i, ble in enumerate([37, 38, 39]):
                x = LEFT + i * (BAR_W + GAP)   # left edge of this bar

                # scale bar height proportionally to the max
                h       = max(1, int(hits[ble] * MAX_H / max_hit))
                bar_top = BAR_Y + (MAX_H - h)   # bars grow upward from bottom

                oled.fill_rect(x, bar_top, BAR_W, h, 1)   # filled bar

                # peak line shows highest point this session, also scaled the same way
                ph = max(1, int(peak[ble] * MAX_H / max_hit))
                oled.hline(x, BAR_Y + (MAX_H - ph), BAR_W, 1)

                # channel label below the bar
                oled.text("ch" + str(ble), x + 4, BAR_Y + MAX_H + 2)

                # hit count above the bar, wraps at 1000 to stay within bar width
                count_str = str(hits[ble] % 1000)
                oled.text(count_str, x + 2, max(10, bar_top - 9))

            oled.hline(0, 54, 128, 1)
            oled.text(T("bt_total") + str(total % 10000), 0, 56)
            oled.text(T("bt_back"), 72, 56)
            oled.show()

        frame += 1
        utime.sleep_ms(10)