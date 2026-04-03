# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_wifi_setup.py, wifi network picker and on screen keyboard
#
# keyboard design:
#   4 rows always visible, no scrolling at all
#   row 0: A-P (uppercase) or a-p (lowercase)
#   row 1: Q-Z + 0-5
#   row 2: 6-9 + space + symbols
#   row 3: more symbols + [DEL] at col 14, [SHF] at col 15
#
#   DEL and SHF are single dedicated keys at the end of row 3
#   they are shown as [D] and [S] to fit in one character cell
#   pressing PWR on [D] deletes last character
#   pressing PWR on [S] toggles shift (upper/lower case)
#
# navigation:
#   up/down = move between rows (wraps)
#   select  = move cursor right (wraps within row)
#   back    = move cursor left (wraps within row)
#   hold back 2s = start connecting with typed password
#   pwr btn = type the highlighted character (or trigger DEL/SHF)
#
# network list:
#   selected network is highlighted with inverted colors
#   scrollbar on right edge shows position

from machine import Pin
import network
import utime
import storage
import buttons
import buzzer
from lang import T

_pwr = Pin(6, Pin.IN, Pin.PULL_DOWN)

# 16 characters per row, all rows same length so col always wraps at 16
# last two columns of row 3 are special keys, shown as [D]elete and [S]hift
ROWS_UPPER = [
    "ABCDEFGHIJKLMNOP",
    "QRSTUVWXYZ012345",
    "6789 !@#$%^&*()-",
    "=+[]{};:',./?[D][S]",   # [D] = delete, [S] = shift -- handled as special below
]
ROWS_LOWER = [
    "abcdefghijklmnop",
    "qrstuvwxyz012345",
    "6789 !@#$%^&*()-",
    "=+[]{};:',./?[D][S]",
]

# the visible characters per row (16 cols, 8px each = 128px wide)
# row 3 last two cells are special, we handle them separately in drawing and input
ROW_LEN = 16

# which column indices in row 3 are special keys
DEL_COL = 14
SHF_COL = 15

def _wait_pwr_release():
    while _pwr.value() == 1:
        utime.sleep_ms(10)
    utime.sleep_ms(50)

def _pwr_pressed():
    if _pwr.value() == 1:
        utime.sleep_ms(50)
        if _pwr.value() == 1:
            _wait_pwr_release()
            return True
    return False

def _draw_keyboard(oled, password, row, col, blink, shift):
    oled.fill(0)

    # header: shift state indicator on the right
    shf_label = "^UP" if shift else "^lo"
    oled.text("PASSWORD", 0, 0)
    oled.text(shf_label, 104, 0)
    oled.hline(0, 9, 128, 1)

    # password field showing last 14 chars + blinking cursor
    display_pw = password[-14:] if len(password) > 14 else password
    if blink:
        display_pw += "_"
    oled.text(display_pw[:16], 0, 11)
    oled.hline(0, 20, 128, 1)

    rows = ROWS_UPPER if shift else ROWS_LOWER

    # draw all 4 rows, no scrolling, they all fit in the remaining 44px
    # each row is 11px tall (8px text + 3px gap)
    for r in range(4):
        y       = 22 + r * 10
        row_str = rows[r]

        for c in range(ROW_LEN):
            x = c * 8

            # determine what to display in this cell
            if r == 3 and c == DEL_COL:
                ch_display = "D"   # delete key shown as D
            elif r == 3 and c == SHF_COL:
                ch_display = "S"   # shift key shown as S
            else:
                ch_display = row_str[c] if c < len(row_str) else " "

            # highlight the selected cell
            if r == row and c == col:
                oled.fill_rect(x, y - 1, 8, 10, 1)
                oled.text(ch_display, x, y, 0)
            else:
                oled.text(ch_display, x, y, 1)

    oled.hline(0, 62, 128, 1)
    oled.show()

def keyboard(oled):
    password = ""
    row      = 0
    col      = 0
    shift    = True    # start uppercase
    blink    = True
    blink_t  = utime.ticks_ms()
    redraw   = True

    while True:
        if utime.ticks_diff(utime.ticks_ms(), blink_t) > 500:
            blink   = not blink
            blink_t = utime.ticks_ms()
            redraw  = True

        if redraw:
            _draw_keyboard(oled, password, row, col, blink, shift)
            redraw = False

        if buttons.up():
            row    = (row - 1) % 4
            redraw = True

        if buttons.down():
            row    = (row + 1) % 4
            redraw = True

        if buttons.select():
            # move cursor right, wrap within row
            col    = (col + 1) % ROW_LEN
            redraw = True

        # back button: tap = move left, hold 2s = confirm and connect
        if buttons.btn_bk.value() == 1:
            t = utime.ticks_ms()
            while buttons.btn_bk.value() == 1:
                held = utime.ticks_diff(utime.ticks_ms(), t)
                if held >= 2000:
                    while buttons.btn_bk.value() == 1:
                        utime.sleep_ms(10)
                    return password if password else None
                if held > 400:
                    # show hint that hold is being detected
                    oled.fill_rect(0, 63, 128, 1, 0)
                    secs = max(0.0, round((2000 - held) / 1000, 1))
                    # flash the password field area to show countdown
                    oled.fill_rect(0, 11, 128, 9, 0)
                    oled.text("hold " + str(secs) + "s=OK", 20, 11)
                    oled.show()
                utime.sleep_ms(20)
            # released before 2s, move cursor left
            utime.sleep_ms(50)
            col    = (col - 1) % ROW_LEN
            redraw = True

        if _pwr_pressed():
            rows = ROWS_UPPER if shift else ROWS_LOWER

            # handle special keys on row 3
            if row == 3 and col == DEL_COL:
                # delete last character
                if password:
                    password = password[:-1]
                buzzer.beep(15)
                redraw = True
            elif row == 3 and col == SHF_COL:
                # toggle shift
                shift  = not shift
                buzzer.beep(15)
                redraw = True
            else:
                # normal character
                ch = rows[row][col] if col < len(rows[row]) else " "
                password += ch
                buzzer.beep(20)
                redraw = True

        utime.sleep_ms(20)

def _draw_network_list(oled, nets, idx):
    oled.fill(0)
    oled.text(T("wifi_title")[:16], 0, 0)
    oled.hline(0, 9, 128, 1)

    visible = nets[idx:idx+3]
    for i, net in enumerate(visible):
        ssid   = net[0].decode("utf-8", "ignore") if net[0] else "hidden"
        rssi   = net[3]
        y      = 12 + i * 16
        actual = idx + i

        ssid_t = ssid[:10]
        rssi_s = str(rssi)
        pad    = " " * max(0, 16 - len(ssid_t) - len(rssi_s))
        line   = (ssid_t + pad + rssi_s)[:16]
        ch_str = "ch" + str(net[2])

        if actual == idx:
            # invert the selected network row so its obvious which one is highlighted
            oled.fill_rect(0, y - 1, 128, 10, 1)
            oled.text(line, 0, y, 0)
            oled.fill_rect(0, y + 8, 80, 8, 1)
            oled.text(ch_str, 0, y + 8, 0)
        else:
            oled.text(line,   0, y,     1)
            oled.text(ch_str, 0, y + 8, 1)

    if len(nets) > 3:
        bar_h = max(4, 48 * 3 // len(nets))
        bar_y = 11 + (48 - bar_h) * idx // max(1, len(nets) - 1)
        oled.vline(126, 11, 48, 1)
        oled.fill_rect(125, 11 + bar_y, 3, bar_h, 1)

    oled.hline(0, 54, 128, 1)
    oled.text(str(idx+1) + "/" + str(len(nets)) + " SEL=pick", 0, 56)
    oled.show()

def run(oled):
    import power

    oled.fill(0)
    oled.text(T("wifi_title"), 0, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("wifi_scanning"), 20, 28)
    oled.show()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    utime.sleep_ms(200)

    try:
        found = wlan.scan()
        found.sort(key=lambda x: x[3], reverse=True)
    except:
        found = []

    if not found:
        oled.fill(0)
        oled.text(T("wifi_title"), 0, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("wifi_none"), 20, 28)
        oled.show()
        utime.sleep_ms(2000)
        wlan.active(False)
        return

    idx    = 0
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
            _draw_network_list(oled, found, idx)
            redraw = False

        if buttons.select():
            ssid = found[idx][0].decode("utf-8", "ignore") if found[idx][0] else ""

            oled.fill(0)
            oled.text("Network:", 0, 0)
            oled.text(ssid[:16], 0, 12)
            oled.text("Opening keyboard", 0, 36)
            oled.show()
            utime.sleep_ms(600)

            password = keyboard(oled)
            if password is None:
                redraw = True
                continue

            oled.fill(0)
            oled.text(T("kb_connect"), 16, 24)
            oled.show()

            wlan.connect(ssid, password)
            t = utime.ticks_ms()
            while not wlan.isconnected():
                if utime.ticks_diff(utime.ticks_ms(), t) > 10000:
                    break
                utime.sleep_ms(200)

            if wlan.isconnected():
                storage.set_setting('wifi_ssid', ssid)
                storage.set_setting('wifi_pass', password)
                buzzer.double()
                oled.fill(0)
                oled.text(T("kb_connected"), 16, 20)
                oled.text(T("kb_saved"),     16, 34)
                oled.show()
                utime.sleep_ms(2000)
                wlan.active(False)
                return
            else:
                buzzer.error()
                oled.fill(0)
                oled.text(T("kb_failed"), 28, 28)
                oled.show()
                utime.sleep_ms(1500)
                redraw = True

        utime.sleep_ms(20)