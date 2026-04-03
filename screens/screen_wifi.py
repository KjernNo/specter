# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_wifi.py, wifi network scanner using the pico w built in radio
# this uses the pico w's own wifi chip, nothing to do with the nrf module
# it does a passive scan and lists all visible networks sorted by signal strength
# strongest signal at the top, weakest at the bottom
#
# the scan result from wlan.scan() returns a tuple for each network:
# (ssid, bssid, channel, rssi, security, hidden)
# rssi is signal strength in dbm, more negative = weaker (e.g. -40 is strong, -90 is weak)
# we sort by rssi descending so strongest networks appear first
#
# the list is scrollable with up/down, showing 3 networks at a time
# each network shows the ssid and rssi on the top line, channel on the line below
# there is a scrollbar on the right edge to show position in the list

import network
import utime
import buttons
import power
from lang import T

def run(oled):
    # show scanning message while the wifi scan runs, it takes a second or two
    oled.fill(0)
    oled.text(T("wifi_title"), 0, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("wifi_scanning"), 20, 28)
    oled.show()

    # activate the wifi interface and run a scan
    # wlan.scan() returns results sorted by rssi which we then sort descending
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    utime.sleep_ms(200)   # brief settle time after activating

    try:
        found = wlan.scan()
        found.sort(key=lambda x: x[3], reverse=True)   # sort strongest first
    except:
        found = []   # scan failed for some reason, show empty list

    if not found:
        # nothing found, show a message and wait for back button
        oled.fill(0)
        oled.text(T("wifi_title"), 0, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("wifi_none"), 20, 28)
        oled.text(T("wifi_found"), 20, 38)
        oled.show()
        while not buttons.back():
            utime.sleep_ms(50)
        wlan.active(False)
        return

    idx    = 0       # index of the top visible network in the list
    redraw = True

    while True:
        if power.check(0):
            wlan.active(False)
            return
        if buttons.back():
            wlan.active(False)
            return

        if buttons.up():
            idx    = max(0, idx - 1)
            redraw = True

        if buttons.down():
            idx    = min(len(found) - 1, idx + 1)
            redraw = True

        if redraw:
            oled.fill(0)
            oled.text(T("wifi_title"), 0, 0)
            oled.hline(0, 9, 128, 1)

            # show 3 networks at a time, each taking 16px (2 rows of 8px text)
            visible = found[idx:idx+3]
            for i, net in enumerate(visible):
                ssid  = net[0].decode("utf-8", "ignore") if net[0] else "hidden"
                rssi  = net[3]   # signal strength in dbm
                ch    = net[2]   # wifi channel number
                y     = 13 + i * 16

                # format: ssid on the left, rssi right aligned on same line
                # pad with spaces manually because micropython doesnt have ljust
                ssid_t = ssid[:10]
                rssi_s = str(rssi)
                pad    = " " * max(0, 16 - len(ssid_t) - len(rssi_s))
                oled.text((ssid_t + pad + rssi_s)[:16], 0, y)
                oled.text("ch" + str(ch), 0, y + 8)

            # draw a simple scrollbar on the right edge
            # bar height is proportional to how many items are visible vs total
            if len(found) > 0:
                bar_h = max(4, 42 * 3 // len(found))
                bar_y = 11 + (42 - bar_h) * idx // max(1, len(found) - 1)
                oled.vline(126, 11, 42, 1)
                oled.fill_rect(125, 11 + bar_y, 3, bar_h, 1)

            oled.hline(0, 54, 128, 1)
            # show current position in list and navigation hint
            count_str = str(idx+1) + "/" + str(len(found)) + " " + T("wifi_back")
            oled.text(count_str[:16], 0, 56)
            oled.show()
            redraw = False

        utime.sleep_ms(50)