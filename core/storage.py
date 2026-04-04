# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# storage.py, handles all persistent data on the pico's flash filesystem
# we store two separate json files in a /data folder to keep things tidy
# specter_data.json holds counters like boots and battery cycles
# specter_settings.json holds all user configurable settings
#
# json was chosen because its human readable if you need to inspect or edit
# the files directly, and micropython has built in json support
#
# the _load function fills in missing keys from defaults automatically
# this means when a firmware update adds a new setting, existing installs
# will get the default value on next boot without any migration code needed
# thats intentional, keep it that way when adding new settings!
#
# version bootstrapping:
# when a new firmware is installed via OTA, a VERSION file lands in the root
# on first boot after install, _bootstrap_version() reads that file, saves
# the version to settings json, then deletes the file so it only runs once
# this keeps the device version accurate without hardcoding it anywhere

import json
import os

DATA_DIR      = '/data'
DATA_PATH     = DATA_DIR + '/specter_data.json'
SETTINGS_PATH = DATA_DIR + '/specter_settings.json'

DATA_DEFAULTS = {
    'boots':        0,     # total number of times the device has booted
    'cycles':       0,     # battery charge cycles (manual tracking for now)
}

SETTINGS_DEFAULTS = {
    'brightness':   100,    # oled contrast value, 0 to 255
    'scan_speed':   200,    # microseconds to listen per channel in spectrum scanner
    'decay':        80,     # bar decay multiplier as integer percent (80 = 0.80 per frame)
    'peak_decay':   97,     # peak marker decay multiplier (slower than bars looks better)
    'batt_update':  10,     # seconds between battery adc refreshes
    'buzzer_on':    1,      # 1 means buzzer is on, 0 means silent
    'language':     'en',   # en = english, no = norwegian bokmal
    'wifi_ssid':    '',     # name of the saved wifi network, empty means none saved
    'wifi_pass':    '',     # password for the saved wifi network
    'version':      '1.0.0',# the currently installed firmware version string
}

def _ensure_dir():
    # create /data if it doesnt exist yet
    # this happens silently on first boot, the try/except is because
    # os.mkdir throws an error if the folder already exists
    try:
        os.mkdir(DATA_DIR)
    except:
        pass

def _load(path, defaults):
    # try to load the json file, fall back to defaults if anything goes wrong
    # the key merging loop at the end is what handles new keys from firmware updates
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
        return data
    except:
        return dict(defaults)

def _save(path, data):
    _ensure_dir()
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except:
        pass   # if it fails we just lose that write, the data will be stale until next save

def _bootstrap_version():
    # if a VERSION file exists in the root, read it and save to settings
    # this file is included in every OTA zip by the github actions workflow
    # it gets extracted to /VERSION on the pico during install
    # we read it once, update the version in settings, then delete it
    # so this only ever runs once per firmware install, not every boot
    VERSION_FILE = '/VERSION'
    try:
        with open(VERSION_FILE, 'r') as f:
            ver = f.read().strip()
        if ver:
            settings = _load(SETTINGS_PATH, SETTINGS_DEFAULTS)
            settings['version'] = ver
            _save(SETTINGS_PATH, settings)
        os.remove(VERSION_FILE)
    except:
        pass   # no VERSION file means either already bootstrapped or fresh micropython install

# -- data functions ---------------------------------------------------

def on_boot():
    # call this once at the very start of main(), increments boot counter
    # also bootstraps version from VERSION file if present after an ota install
    # returns the full data dict so callers can read it without a second load
    _ensure_dir()
    _bootstrap_version()   # reads /VERSION, updates settings, deletes file
    data = _load(DATA_PATH, DATA_DEFAULTS)
    data['boots'] += 1
    _save(DATA_PATH, data)
    return data

def add_cycle():
    # increment the battery cycle counter
    # currently not called automatically, reserved for future use
    # when we add proper charge cycle detection via the battery voltage
    data = _load(DATA_PATH, DATA_DEFAULTS)
    data['cycles'] += 1
    _save(DATA_PATH, data)

def get():
    # returns the full data dict, used by stats screen
    return _load(DATA_PATH, DATA_DEFAULTS)

# -- settings functions -----------------------------------------------

def get_settings():
    # returns the full settings dict
    return _load(SETTINGS_PATH, SETTINGS_DEFAULTS)

def save_settings(settings):
    # saves the full settings dict back to flash
    _save(SETTINGS_PATH, settings)

def get_setting(key):
    # shortcut to read a single setting by key
    # falls back to the default value if the key doesnt exist
    return get_settings().get(key, SETTINGS_DEFAULTS.get(key))

def set_setting(key, value):
    # shortcut to write a single setting by key
    # loads the full dict, changes one value, saves it back
    settings = get_settings()
    settings[key] = value
    save_settings(settings)
