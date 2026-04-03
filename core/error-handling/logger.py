# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# logger.py, simple error logger for SPECTER
# writes errors to /data/specter_log.txt with a timestamp (ticks_ms since boot)
# keeps the last MAX_LINES lines only so the file never grows unbounded
# the log can be read from the settings screen under "Error Log"
#
# usage:
#   import logger
#   logger.log("something went wrong: " + str(e))
#
# the log file is plain text, one entry per line, newest at the bottom
# each line looks like: [123456ms] screen_wifi: OSError: [Errno 5] EIO

import utime
import os

LOG_PATH  = '/data/specter_log.txt'
MAX_LINES = 30   # keep last 30 errors, more than enough for debugging

def _ensure():
    try:
        os.mkdir('/data')
    except:
        pass

def log(message):
    # write a timestamped error entry to the log file
    # if the file gets too long, trim it to MAX_LINES
    _ensure()
    entry = "[" + str(utime.ticks_ms()) + "ms] " + str(message)
    try:
        # read existing lines
        try:
            with open(LOG_PATH, 'r') as f:
                lines = f.read().splitlines()
        except:
            lines = []

        # append new entry and trim to max lines
        lines.append(entry)
        if len(lines) > MAX_LINES:
            lines = lines[-MAX_LINES:]

        # write back
        with open(LOG_PATH, 'w') as f:
            f.write('\n'.join(lines) + '\n')
    except:
        pass   # if logging itself fails just silently skip it

def read():
    # returns list of log lines, newest last
    try:
        with open(LOG_PATH, 'r') as f:
            return f.read().splitlines()
    except:
        return []

def clear():
    try:
        with open(LOG_PATH, 'w') as f:
            f.write('')
    except:
        pass