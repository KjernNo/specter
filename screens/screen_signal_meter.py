# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_signal_meter.py, live 2.4ghz signal strength meter
# scans a single channel repeatedly and shows how often a carrier is detected
# the detection rate over a rolling window gives a rough signal strength indication
# think of it like a metal detector but for 2.4ghz radio signals
#
# you can point the antenna (or the board itself) at a transmitter and watch
# the bar rise and fall as you move closer or further away
# useful for finding where interference is coming from or locating a transmitter
#
# up/down changes the channel being monitored so you can tune to a specific frequency
# the channel maps to frequency as: 2400 + channel = mhz
# so channel 1 = 2401mhz, channel 6 = 2406mhz (wifi ch1), channel 40 = 2440mhz etc.
#
# the strength is calculated as a rolling average of the last WINDOW scans
# each scan either detects a carrier (1) or not (0)
# averaging these gives a 0.0-1.0 signal strength value
# this is then displayed as a large bar filling most of the screen
# plus a numerical percentage and the raw detection count

import utime
import nrf
import buttons
import power

DISP_W  = 128
BAR_H   = 36    # height of the big signal bar in pixels
BAR_Y   = 12    # y position of the top of the bar
WINDOW  = 40    # number of recent scans to average for signal strength

# some useful channel presets shown in the hint at the bottom
# wifi ch1=2, wifi ch6=27, wifi ch11=52, ble adv=2/26/80
CHANNEL_MIN = 0
CHANNEL_MAX = 80

def run(oled):
    channel  = 2      # start on ble advertising ch37 = nrf ch2
    samples  = []     # rolling window of recent scan results (0 or 1 each)
    strength = 0.0    # current signal strength 0.0 to 1.0
    peak     = 0.0    # highest strength seen since screen opened
    redraw   = True
    frame    = 0

    while True:
        if power.check(0):
            return
        if buttons.back():
            return

        if buttons.up():
            channel = min(CHANNEL_MAX, channel + 1)
            samples = []   # clear samples when channel changes so old data doesnt mislead
            peak    = 0.0
            redraw  = True

        if buttons.down():
            channel = max(CHANNEL_MIN, channel - 1)
            samples = []
            peak    = 0.0
            redraw  = True

        # scan the selected channel and add to rolling window
        hit = nrf.scan_channel(channel)
        samples.append(hit)
        if len(samples) > WINDOW:
            samples.pop(0)   # drop oldest sample to keep window size fixed

        # strength is the fraction of recent scans that detected a carrier
        strength = sum(samples) / max(len(samples), 1)
        if strength > peak:
            peak = strength

        # redraw every 5 scans so the display updates smoothly without slowing scanning
        if frame % 5 == 0:
            oled.fill(0)

            # channel and frequency in header
            freq_mhz = 2400 + channel
            oled.text("SIGNAL METER", 16, 0)
            oled.hline(0, 9, 128, 1)

            # big signal bar, fills horizontally based on strength
            bar_w = int(DISP_W * strength)
            oled.rect(0, BAR_Y, DISP_W, BAR_H, 1)   # outer border
            if bar_w > 2:
                oled.fill_rect(1, BAR_Y + 1, bar_w - 2, BAR_H - 2, 1)

            # peak marker as a vertical line inside the bar border
            peak_x = int(DISP_W * peak)
            if peak_x > 1:
                oled.vline(min(peak_x, DISP_W - 2), BAR_Y + 1, BAR_H - 2, 1)

            # percentage readout centered below the bar
            pct_str = str(int(strength * 100)) + "%"
            oled.text(pct_str, (DISP_W - len(pct_str) * 8) // 2, BAR_Y + BAR_H + 3)

            oled.hline(0, 54, 128, 1)

            # channel info and peak on bottom line
            ch_str = "CH:" + str(channel) + " " + str(freq_mhz) + "MHz"
            oled.text(ch_str[:16], 0, 56)
            oled.show()
            redraw = False

        frame += 1
        utime.sleep_ms(5)