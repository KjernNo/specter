# SPECTER Firmware, https://github.com/KjernNo/specter
# Copyright (C) 2026 Phillip Rødseth / Kjern.no
# SPDX-License-Identifier: CERN-OHL-W-2.0
# NOTICE: Products with a display must show "SPECTER / by Kjern" (or equivalent)
# visibly on boot. See NOTICE.md for full attribution requirements.

# nrf.py, bare metal driver for the nrf24l01 radio module
# this is RX only, we never transmit anything
# the nrf24l01 is used purely for passive scanning, specifically using the
# carrier detect feature which tells us if any signal is present on a channel
# without actually decoding what it is
#
# the nrf communicates over spi, all configuration is done by reading and
# writing registers over spi using specific command bytes from the datasheet
# register addresses and command bytes are all from the nrf24l01 datasheet
# if you want to understand why specific values are written, look up the
# corresponding register in the datasheet, its well documented

import utime
from hw import spi, csn, ce

def _write(reg, val):
    # write a single byte value to a register
    # the write command is 0x20 OR'd with the register address (sets the write bit)
    # csn goes low to start the transaction, high to end it
    csn.value(0)
    spi.write(bytes([0x20 | reg, val]))
    csn.value(1)

def _read(reg):
    # read a single byte from a register
    # mask the address to 5 bits as required by the nrf datasheet
    # we send the address then clock in the response byte
    csn.value(0)
    spi.write(bytes([reg & 0x1F]))
    d = spi.read(1)
    csn.value(1)
    return d[0]

def _cmd(c):
    # send a standalone command byte with no data
    # used for flush commands (0xE1 = flush tx, 0xE2 = flush rx)
    csn.value(0)
    spi.write(bytes([c]))
    csn.value(1)

def init():
    # initialise the nrf24l01 in rx mode ready for carrier detect scanning
    # the nrf needs 100ms after power on before it will respond to spi commands
    # if you skip this sleep you often get 0xFF back from all registers
    csn.value(1)
    ce.value(0)
    utime.sleep_ms(100)

    _write(0x00, 0x03)   # config register, pwr_up=1 (powered on), prim_rx=1 (receive mode)
    utime.sleep_ms(5)    # config register needs 5ms to take effect after pwr_up
    _write(0x01, 0x00)   # en_aa, disable auto acknowledgement, not needed for scanning
    _write(0x02, 0x01)   # en_rxaddr, enable pipe 0 only
    _write(0x03, 0x03)   # setup_aw, 5 byte address width
    _write(0x04, 0x00)   # setup_retr, no retransmission
    _write(0x06, 0x0F)   # rf_setup, 2mbps data rate, 0dbm output power
    _write(0x11, 0x20)   # rx_pw_p0, 32 byte payload size on pipe 0
    _write(0x1C, 0x00)   # dynpd, disable dynamic payload length
    _write(0x1D, 0x00)   # feature register, disable all extra features
    _cmd(0xE1)           # flush tx fifo, clear any leftover data
    _cmd(0xE2)           # flush rx fifo, clear any leftover data

    s = _read(0x07)
    # the status register should return something between 0x01 and 0xFE on a healthy nrf
    # 0x00 means nothing responded at all (usually csn/miso wiring issue)
    # 0xFF means spi is completely dead (usually mosi/sck wiring issue or no power)
    return s not in (0x00, 0xFF)

def status():
    # read the status register, used to check if the nrf is still alive
    # and to get the raw value for display in the stats screen
    return _read(0x07)

def scan_channel(ch):
    # tune the nrf to a specific channel and check for any carrier signal
    # returns 1 if something is transmitting on that channel, 0 if its quiet
    # the carrier detect register (0x09) bit 0 is set when the nrf detects
    # a signal stronger than -64dbm on the current channel
    # we listen for 200 microseconds which is enough to catch most signals
    # bluetooth and wifi both transmit long enough to be detected in 200us
    ce.value(0)
    _write(0x05, ch)     # rf_ch register, sets the channel (2400 + ch MHz)
    _write(0x00, 0x03)   # keep config in rx mode (ce.value(1) activates it)
    ce.value(1)
    utime.sleep_us(200)
    cd = _read(0x09) & 0x01   # read carrier detect bit
    ce.value(0)
    return cd