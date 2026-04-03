# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_log.py, error log viewer for SPECTER
# reads specter_log.txt and shows entries on the oled
# up/down scrolls through entries, select clears the log, back exits
# each entry is shown truncated to 16 chars to fit the display
# if you need to see the full entry, read the file directly in thonny

import utime
import logger
import buttons
import power

def run(oled):
    lines  = logger.read()
    idx    = max(0, len(lines) - 1)   # start at the newest entry
    redraw = True

    while True:
        if power.check(0):
            return
        if buttons.back():
            return

        if buttons.up():
            idx    = max(0, idx - 1)
            redraw = True

        if buttons.down():
            idx    = min(max(0, len(lines) - 1), idx + 1)
            redraw = True

        if buttons.select():
            # clear the log on select, ask for confirmation first
            oled.fill(0)
            oled.text("Clear log?", 20, 20)
            oled.text("SEL=yes BK=no", 8, 36)
            oled.show()
            confirmed = False
            while True:
                if buttons.select():
                    confirmed = True
                    break
                if buttons.back():
                    break
                utime.sleep_ms(20)
            if confirmed:
                logger.clear()
                lines  = []
                idx    = 0
            redraw = True

        if redraw:
            oled.fill(0)
            oled.text("ERROR LOG", 24, 0)
            oled.hline(0, 9, 128, 1)

            if not lines:
                oled.text("No errors :)", 16, 28)
                oled.text("All good!", 24, 40)
            else:
                # show 3 log entries at a time
                # each entry gets 2 lines: timestamp on top, message below
                visible_start = max(0, min(idx, len(lines) - 3))
                for i, line in enumerate(lines[visible_start:visible_start+3]):
                    y      = 12 + i * 16
                    actual = visible_start + i

                    # split timestamp and message if possible
                    if ']' in line:
                        parts = line.split('] ', 1)
                        ts  = parts[0] + ']'
                        msg = parts[1] if len(parts) > 1 else ''
                    else:
                        ts  = ''
                        msg = line

                    # highlight current entry
                    if actual == idx:
                        oled.fill_rect(0, y - 1, 128, 10, 1)
                        oled.text(ts[:16],  0, y,     0)
                        oled.text(msg[:16], 0, y + 8, 1)
                    else:
                        oled.text(ts[:16],  0, y,     1)
                        oled.text(msg[:16], 0, y + 8, 1)

                # scrollbar
                if len(lines) > 3:
                    bar_h = max(4, 42 * 3 // len(lines))
                    bar_y = 11 + (42 - bar_h) * idx // max(1, len(lines) - 1)
                    oled.vline(126, 11, 42, 1)
                    oled.fill_rect(125, 11 + bar_y, 3, bar_h, 1)

            oled.hline(0, 54, 128, 1)
            count = str(idx + 1) + "/" + str(max(len(lines), 1))
            oled.text(count, 0, 56)
            oled.text("SEL=clear BK=bk", 32, 56)
            oled.show()
            redraw = False

        utime.sleep_ms(50)