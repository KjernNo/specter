# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_spectrum.py, live 2.4ghz spectrum analyzer
# this is probably the coolest screen in specter :)
# it scans all 78 channels from 2402mhz to 2480mhz and draws a live bar graph
# the nrf24l01 carrier detect feature tells us if any signal is present on each channel
# we stretch 78 channels across 128 display columns so the full band fills the screen
#
# the decay system makes the bars fall smoothly instead of snapping to 0
# each frame we multiply the bar height by the decay value (e.g. 0.80)
# so a bar that was full height drops to 80%, then 64%, then 51% etc.
# this makes wifi channels look like solid blocks and bluetooth look like
# short spikes jumping around because bluetooth hops channels so fast
#
# the peak dots are separate from the bars and decay much slower (0.97 per frame)
# they float above the bars showing where the highest recent activity was
# makes it easy to spot which channels are busiest even when activity is intermittent
#
# settings used from storage: scan_speed, decay, peak_decay
# these can all be tuned in the settings screen

import utime
import nrf
import buttons
import power
import storage
from lang import T

# 78 channels covers the full bluetooth and wifi 2.4ghz band (ch2 to ch79)
# channel number maps directly to frequency: 2400 + ch = frequency in mhz
# so ch2 = 2402mhz, ch79 = 2479mhz
NUM_CH    = 78
DISP_W    = 128   # display is 128 pixels wide

# layout constants, these are pixel values for the oled layout
HEADER_H  = 11    # pixels taken up by the title and separator line at the top
FOOTER_H  = 9     # pixels taken up by the status line at the bottom
# the bars fill the space between header and footer, minus 2px for separators
MAX_BAR_H = 64 - HEADER_H - FOOTER_H - 2   # = 42 pixels max bar height

def col_to_ch(col):
    # converts a display column (0 to 127) to an nrf channel number (2 to 79)
    # we spread 78 channels across 128 pixels so each channel gets about 1.6px
    return 2 + int(col * NUM_CH / DISP_W)

def run(oled):
    # load settings once when the screen opens
    # if the user changes settings we pick them up next time they open this screen
    s          = storage.get_settings()
    scan_us    = s.get('scan_speed', 200)           # microseconds to listen per channel
    decay      = s.get('decay', 80) / 100.0         # convert 80 to 0.80 for multiplication
    peak_decay = s.get('peak_decay', 97) / 100.0    # convert 97 to 0.97

    # smooth[] holds the current bar height for each display column, 0.0 to 1.0
    # peak[] holds the peak marker height for each column, also 0.0 to 1.0
    smooth     = [0.0] * DISP_W
    peak       = [0.0] * DISP_W
    total_hits = 0   # running count of how many times a signal was detected
    last_ch    = -1  # last channel that had any activity this session
    max_ch     = -1  # the channel with the strongest current signal

    while True:
        if power.check(0):
            return   # power button tapped, redraw will happen in caller
        if buttons.back():
            return   # back button exits to menu

        max_val = 0.0
        max_col = -1

        # scan every display column, which maps to an nrf channel
        for col in range(DISP_W):
            ch  = col_to_ch(col)
            hit = nrf.scan_channel(ch)   # returns 1 if signal detected, 0 if quiet

            if hit:
                smooth[col] = 1.0    # signal detected, jump bar to full height
                total_hits += 1
                last_ch = ch
            else:
                smooth[col] *= decay   # no signal, multiply by decay to drop bar smoothly

            # peak marker rises instantly with the bar but falls much slower
            if smooth[col] >= peak[col]:
                peak[col] = smooth[col]
            else:
                peak[col] *= peak_decay

            # track which column has the highest value this frame
            if smooth[col] > max_val:
                max_val = smooth[col]
                max_col = col

        # only report a busiest channel if its actually showing some signal
        max_ch = col_to_ch(max_col) if max_col >= 0 and max_val > 0.1 else -1

        # draw everything
        oled.fill(0)
        oled.text(T("spec_title"), 0, 0)
        oled.hline(0, 9, 128, 1)

        for col in range(DISP_W):
            # draw the bar, height scaled from 0.0-1.0 to 0-MAX_BAR_H pixels
            h = int(smooth[col] * MAX_BAR_H)
            if h > 0:
                # bars grow upward from the bottom of the bar area
                oled.vline(col, HEADER_H + (MAX_BAR_H - h), h, 1)

            # draw the peak dot as a single pixel above the bar
            ph = int(peak[col] * MAX_BAR_H)
            if ph > 0:
                oled.pixel(col, HEADER_H + (MAX_BAR_H - ph), 1)

        # separator above footer
        sep_y = HEADER_H + MAX_BAR_H + 1
        oled.hline(0, sep_y, 128, 1)

        # footer shows hit count, last active channel, and peak channel
        # H = total hits since opening screen
        # L = last channel that had any activity (watch this to see bt hopping!)
        # P = channel with strongest current signal
        fy = sep_y + 2
        oled.text("H:" + str(total_hits % 10000), 0,  fy)
        oled.text("L:" + (str(last_ch) if last_ch >= 0 else "--"), 50, fy)
        oled.text("P:" + (str(max_ch)  if max_ch  >= 0 else "--"), 92, fy)
        oled.show()