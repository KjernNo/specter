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
#   GET /update/version  returns json. ex. {"version": "1.0.1"}
#   GET /update/latest   returns a zip file containing the new firmware files
#
# the zip extractor handles both stored (method 0) and deflated (method 8) files
# deflated means compressed with zlib/deflate which is standard zip compression
# micropython has uzlib for decompression which handles this
#
# version comparison works by splitting "1.0.1" into (1, 0, 1) tuples
# and comparing them element by element, so 1.0.2 > 1.0.1 etc.
#
# wifi credentials must be saved first via the wifi setup screen
# if no ssid is saved, we show a message telling the user to set up wifi first
#
# the progress bar shows download progress based on content-length header
# and install progress based on how many files have been extracted vs total

import network
import utime
import os
import storage
import buttons
import buzzer
from lang import T

SPECTER_VERSION = "1.0.0"
UPDATE_URL      = "http://specter.kjern.no/update/latest"
VERSION_URL     = "http://specter.kjern.no/update/version"

def _connect_wifi(oled):
    # connect to the saved wifi network, returns the wlan object if successful
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

    # if already connected from a previous operation, reuse the connection
    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, pwd)
    t = utime.ticks_ms()
    while not wlan.isconnected():
        if utime.ticks_diff(utime.ticks_ms(), t) > 15000:   # 15 second timeout
            return None
        utime.sleep_ms(300)
    return wlan

def _draw_progress(oled, label, pct):
    # draws a progress bar with label and percentage
    # used for both download and install phases
    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(label[:16], 0, 18)
    oled.rect(0, 32, 128, 12, 1)   # outer border of progress bar
    filled = int(126 * pct / 100)
    if filled > 0:
        oled.fill_rect(1, 33, filled, 10, 1)   # filled portion
    oled.text(str(pct) + "%", 52, 48)
    oled.show()

def _extract_zip(oled, data):
    # minimal zip extractor written for micropython
    # parses the zip local file headers manually using ustruct
    # supports method 0 (stored, no compression) and method 8 (deflated)
    # files are written directly to the pico filesystem at their path in the zip
    # parent directories are created automatically if they dont exist
    #
    # the zip format starts each file with a local file header signature PK\x03\x04
    # we scan through the data looking for these signatures
    # each header contains the filename length, extra field length, compression method,
    # compressed size and uncompressed size which we use to extract each file
    import uzlib
    import ustruct

    pos       = 0
    total_sig = b'PK\x03\x04'

    # count total files first so we can show accurate progress
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

        # parse the local file header fields
        # all multi-byte values are little endian
        pos      += 4
        pos      += 2   # version needed
        pos      += 2   # general purpose flag
        method    = ustruct.unpack('<H', data[pos:pos+2])[0]; pos += 2
        pos      += 4   # last mod time and date
        pos      += 4   # crc32
        comp_sz   = ustruct.unpack('<I', data[pos:pos+4])[0]; pos += 4
        uncomp_sz = ustruct.unpack('<I', data[pos:pos+4])[0]; pos += 4
        fname_len = ustruct.unpack('<H', data[pos:pos+2])[0]; pos += 2
        extra_len = ustruct.unpack('<H', data[pos:pos+2])[0]; pos += 2
        fname     = data[pos:pos+fname_len].decode('utf-8'); pos += fname_len
        pos      += extra_len   # skip extra field

        file_data  = data[pos:pos+comp_sz]
        pos       += comp_sz

        if fname.endswith('/'):
            # directory entry, just create the folder
            try:
                os.mkdir('/' + fname.rstrip('/'))
            except:
                pass
            continue

        # decompress if needed
        if method == 8:
            file_data = uzlib.decompress(file_data, -15)   # -15 means raw deflate
        elif method != 0:
            continue   # unsupported compression method, skip this file

        # create parent directories if they dont exist
        full_path = '/' + fname
        parts = full_path.split('/')
        for i in range(2, len(parts)):
            d = '/'.join(parts[:i])
            try:
                os.mkdir(d)
            except:
                pass   # already exists, fine

        # write the file
        with open(full_path, 'wb') as f:
            f.write(file_data)

        done += 1
        pct   = int(done * 100 / max(count, 1))
        _draw_progress(oled, T("ota_installing"), pct)

def run(oled):
    import power
    import urequests   # micropython http library, not available by default on all builds

    # check that wifi has been set up before we even try anything
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

    # connect to wifi
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

    # fetch the current version from the server
    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_checking"), 20, 28)
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
        # convert "1.2.3" to (1, 2, 3) for easy comparison
        try:
            return tuple(int(x) for x in v.split('.'))
        except:
            return (0, 0, 0)

    if ver_tuple(remote_ver) <= ver_tuple(SPECTER_VERSION):
        # already on the latest version
        buzzer.beep(40)
        oled.fill(0)
        oled.text(T("ota_title"), 36, 0)
        oled.hline(0, 9, 128, 1)
        oled.text(T("ota_up_to_date"), 0, 24)
        oled.text(T("version") + SPECTER_VERSION, 0, 36)
        oled.show()
        utime.sleep_ms(2000)
        wlan.active(False)
        return

    # new version available, ask the user if they want to install it
    oled.fill(0)
    oled.text(T("ota_title"), 36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_found"),   0, 12)
    oled.text(T("version") + remote_ver, 0, 24)
    oled.hline(0, 34, 128, 1)
    oled.text(T("ota_install"), 0, 38)
    oled.text(T("ota_cancel"),  0, 50)
    oled.show()

    # wait for select (install) or back (cancel)
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

    # user confirmed, start downloading
    _draw_progress(oled, T("ota_downloading"), 0)
    try:
        r     = urequests.get(UPDATE_URL, timeout=30)
        total = int(r.headers.get('Content-Length', 0))
        data  = bytearray()
        chunk = 4096   # read in 4kb chunks to avoid running out of ram
        while True:
            buf = r.raw.read(chunk)
            if not buf:
                break
            data.extend(buf)
            if total > 0:
                pct = int(len(data) * 100 / total)
                _draw_progress(oled, T("ota_downloading"), pct)
        r.close()
    except Exception as e:
        buzzer.error()
        oled.fill(0)
        oled.text(T("ota_failed"), 8, 28)
        oled.show()
        utime.sleep_ms(2000)
        wlan.active(False)
        return

    # extract and install the zip
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

    # save the new version number and reboot
    storage.set_setting('version', remote_ver)
    wlan.active(False)

    buzzer.startup()
    oled.fill(0)
    oled.text(T("ota_title"),    36, 0)
    oled.hline(0, 9, 128, 1)
    oled.text(T("ota_rebooting"), 8, 28)
    oled.show()
    utime.sleep_ms(1500)

    from machine import reset
    reset()