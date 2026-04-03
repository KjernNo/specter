# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# screen_ota.py, over the air firmware update screen
# connects to specter.kjern.no to check if a newer firmware version exists
# if one is found, asks the user if they want to install it
# downloads the update as a zip file, extracts it, replaces existing files, reboots
#
# the update server has two endpoints:
#   GET /update/version  returns json like {"version": "1.0.2"}
#   GET /update/latest   returns a 302 redirect to the github release zip
#
# urequests on pico w follows redirects automatically so the redirect is
# transparent -- we just get the zip file at the end of the chain
#
# version is read from storage so it stays correct after an ota update
# the zip extractor handles stored (method 0) and deflated (method 8) files
# wifi credentials must be saved first via the wifi setup screen

import network
import utime
import os
import storage
import buttons
import buzzer
from lang import T

# read version from settings so it reflects the actual installed version
# falls back to 1.0.0 if nothing is saved (fresh install)
def _get_current_version():
    return storage.get_setting('version') or "1.0.0"

# use http not https -- urequests on pico w can struggle with ssl on some servers
# nginx on the server handles ssl termination, the internal flask app is http
# the redirect from /update/latest goes to github which is https but
# urequests handles that redirect fine since github's ssl is standard
UPDATE_URL  = "http://specter.kjern.no/update/latest"
VERSION_URL = "http://specter.kjern.no/update/version"

def _connect_wifi(oled):
    # connect to the saved wifi network, returns wlan object if successful
    # returns None if no credentials are saved or connection times out
    ssid = storage.get_setting('wifi_ssid')
    pwd  = storage.get_setting('wifi_pass')
    if not ssid:
        return None

    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_connecting"), 0, 28)
    oled.show()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan   # already connected, reuse it

    wlan.connect(ssid, pwd)
    t = utime.ticks_ms()
    while not wlan.isconnected():
        if utime.ticks_diff(utime.ticks_ms(), t) > 15000:
            return None
        utime.sleep_ms(300)
    return wlan

def _draw_progress(oled, label, pct):
    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(label[:16], 0, 18)
    oled.rect(0, 32, 128, 12, 1)
    filled = int(126 * pct / 100)
    if filled > 0:
        oled.fill_rect(1, 33, filled, 10, 1)
    oled.text(str(pct) + "%", 52, 48)
    oled.show()

def _extract_zip(oled, data):
    # minimal zip extractor for micropython
    # handles method 0 (stored) and method 8 (deflated)
    # scans for PK\x03\x04 local file header signatures and extracts each file
    # creates parent directories automatically
    import uzlib
    import ustruct

    pos       = 0
    total_sig = b'PK\x03\x04'

    # count files first for accurate progress bar
    count = 0
    tmp   = 0
    while tmp < len(data) - 4:
        if data[tmp:tmp+4] == total_sig:
            count += 1
        tmp += 1

    _draw_progress(oled, T("ota_installing"), 0)

    done = 0
    while pos < len(data) - 4:
        if data[pos:pos+4] != total_sig:
            pos += 1
            continue

        pos      += 4
        pos      += 2   # version needed
        pos      += 2   # general purpose flag
        method    = ustruct.unpack('<H', data[pos:pos+2])[0]; pos += 2
        pos      += 4   # mod time/date
        pos      += 4   # crc32
        comp_sz   = ustruct.unpack('<I', data[pos:pos+4])[0]; pos += 4
        uncomp_sz = ustruct.unpack('<I', data[pos:pos+4])[0]; pos += 4
        fname_len = ustruct.unpack('<H', data[pos:pos+2])[0]; pos += 2
        extra_len = ustruct.unpack('<H', data[pos:pos+2])[0]; pos += 2
        fname     = data[pos:pos+fname_len].decode('utf-8'); pos += fname_len
        pos      += extra_len

        file_data  = data[pos:pos+comp_sz]
        pos       += comp_sz

        if fname.endswith('/'):
            try:
                os.mkdir('/' + fname.rstrip('/'))
            except:
                pass
            continue

        if method == 8:
            file_data = uzlib.decompress(file_data, -15)
        elif method != 0:
            continue

        full_path = '/' + fname
        parts = full_path.split('/')
        for i in range(2, len(parts)):
            d = '/'.join(parts[:i])
            try:
                os.mkdir(d)
            except:
                pass

        with open(full_path, 'wb') as f:
            f.write(file_data)

        done += 1
        _draw_progress(oled, T("ota_installing"), int(done * 100 / max(count, 1)))

def run(oled):
    import power
    import urequests

    current_ver = _get_current_version()

    # check wifi is set up
    ssid = storage.get_setting('wifi_ssid')
    if not ssid:
        oled.fill(0)
        oled.text(T("ota_title"), 36, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("ota_no_wifi"), 0, 24)
        oled.text(T("set_wifi"),    0, 36)
        oled.show()
        utime.sleep_ms(2500)
        return

    wlan = _connect_wifi(oled)
    if not wlan:
        buzzer.error()
        oled.fill(0)
        oled.text(T("ota_title"), 36, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("kb_failed"), 20, 28)
        oled.show()
        utime.sleep_ms(2000)
        return

    # check version on server
    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_checking"), 20, 28)
    oled.text(T("ota_current") + current_ver, 0, 42)
    oled.show()

    try:
        r          = urequests.get(VERSION_URL, timeout=10)
        remote     = r.json()
        r.close()
        remote_ver = remote.get('version', '0.0.0')
    except Exception as e:
        buzzer.error()
        oled.fill(0)
        oled.text(T("ota_title"), 36, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("ota_failed"), 8, 20)
        oled.text((T("ota_error") + str(e))[:16], 0, 34)
        oled.show()
        utime.sleep_ms(2500)
        wlan.active(False)
        return

    def ver_tuple(v):
        try:
            return tuple(int(x) for x in v.split('.'))
        except:
            return (0, 0, 0)

    if ver_tuple(remote_ver) <= ver_tuple(current_ver):
        # already up to date
        buzzer.beep(40)
        oled.fill(0)
        oled.text(T("ota_title"), 36, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("ota_up_to_date"), 0, 20)
        oled.text(T("version") + current_ver, 0, 34)
        oled.show()
        utime.sleep_ms(2000)
        wlan.active(False)
        return

    # new version available, ask user
    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_found"),              0, 12)
    oled.text(T("version") + remote_ver,   0, 22)
    oled.text(T("ota_current") + current_ver, 0, 32)
    oled.hline(0, 42, 128, 1)
    oled.text(T("ota_install"),            0, 46)
    oled.text(T("ota_cancel"),             0, 56)
    oled.show()

    while True:
        if power.check(0):
            wlan.active(False)
            return
        if buttons.back():
            wlan.active(False)
            return
        if buttons.select():
            break
        utime.sleep_ms(20)

    # download -- urequests follows the 302 redirect from /update/latest
    # to the actual github release zip automatically
    _draw_progress(oled, T("ota_downloading"), 0)
    try:
        r     = urequests.get(UPDATE_URL, timeout=60)   # longer timeout for big zip
        total = int(r.headers.get('Content-Length', 0))
        data  = bytearray()
        chunk = 4096
        while True:
            buf = r.raw.read(chunk)
            if not buf:
                break
            data.extend(buf)
            if total > 0:
                _draw_progress(oled, T("ota_downloading"), int(len(data) * 100 / total))
        r.close()
    except Exception as e:
        buzzer.error()
        oled.fill(0)
        oled.text(T("ota_failed"), 8, 28)
        oled.text((T("ota_error") + str(e))[:16], 0, 40)
        oled.show()
        utime.sleep_ms(2000)
        wlan.active(False)
        return

    # extract and install
    try:
        _extract_zip(oled, bytes(data))
    except Exception as e:
        buzzer.error()
        oled.fill(0)
        oled.text(T("ota_failed"), 8, 20)
        oled.text((T("ota_error") + str(e))[:16], 0, 34)
        oled.show()
        utime.sleep_ms(2500)
        wlan.active(False)
        return

    # save new version to settings so device knows what it is after reboot
    storage.set_setting('version', remote_ver)
    wlan.active(False)

    buzzer.startup()
    oled.fill(0)
    oled.text(T("ota_title"),     36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_rebooting"),  8, 28)
    oled.show()
    utime.sleep_ms(1500)

    from machine import reset
    reset()