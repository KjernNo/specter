# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# lang.py, translation loader for SPECTER
# reads all ui strings from /core/languages/strings.json
# the json file is the source of truth for all text shown on screen
# this file just loads it and provides the T() function to access it
#
# to add a new language, just add a new key to each entry in strings.json
# for example add "de": "German text" to each entry and set language to "de"
# nothing in this file needs to change
#
# the strings are cached in memory after the first load so we dont
# read the filesystem every time a screen calls T()
# if you update strings.json via ota, call reload() to pick up the changes

import json
import storage

_strings = None   # None means not loaded yet, gets populated on first T() call

def _load():
    global _strings
    if _strings is None:
        with open('/core/languages/strings.json', 'r') as f:
            _strings = json.load(f)

def T(key):
    # returns the string for the given key in the current language
    # if the key exists but the current language doesnt have it, falls back to english
    # if the key doesnt exist at all, returns the key name itself as a fallback
    # that way missing strings show up obviously in the ui rather than crashing
    _load()
    lang  = storage.get_setting('language') or 'en'
    entry = _strings.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get('en', key))

def reload():
    # forces a fresh load from disk on the next T() call
    # useful after an ota update that includes a new strings.json
    global _strings
    _strings = None
    _load()