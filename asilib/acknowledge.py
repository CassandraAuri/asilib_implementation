"""
Print an acknowledgment statement once per ASI import. This leaves
"""
from datetime import datetime
import configparser
import dateutil.parser

import asilib

CONFIG_PATH = asilib.config['ASILIB_DIR'] / 'config.ini'

def acknowledge(asi:str, dt:float=None) -> bool:
    return False
