#!/usr/bin/env python

#############################################################################
# Mellanox
#
# Platform and model specific eeprom subclass, inherits from the base class,
# and provides the followings:
# - the eeprom format definition
# - specific encoder/decoder if there is special need
#############################################################################

try:
    import exceptions
    import binascii
    import time
    import optparse
    import warnings
    import os
    import sys
    import eeprom_base
    import eeprom_tlvinfo
    import subprocess
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

class board(eeprom_tlvinfo.TlvInfoDecoder):

    _TLV_INFO_MAX_LEN = 256

    def __init__(self, name, path, cpld_root, ro):
        self.eeprom_path = "/sys/class/i2c-adapter/i2c-8/8-0051/eeprom"
        super(board, self).__init__(self.eeprom_path, 0, '', True)

