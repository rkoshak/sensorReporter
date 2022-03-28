"""Utility functions of general use.

Functions:
    - set_log_level: Sets the logging level on the passed in logger to the level
    equivalent to the passed "Level" property in params.
    - issage: returns False if the passed in ag contains unsafe characters to use
    on the command line.
"""
import logging
from configparser import NoOptionError

def set_log_level(params, logger):
    """Expects a params with a Level property. If there is no property the
    default level of INFO is used. Supports all the standard Python logging
    levels. Sets the level of the passed in logger based on the params Level
    property.
    """
    level = None
    try:
        level = params("Level")
    except NoOptionError:
        pass

    levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR"   : logging.ERROR,
        "WARNING" : logging.WARNING,
        "INFO"    : logging.INFO,
        "DEBUG"   : logging.DEBUG,
        "NOTSET"  : logging.NOTSET
    }

    if level:
        logger.setLevel(levels.get(level, logging.NOTSET))

def issafe(arg):
    """Returns False if arg contains ';' or '|'."""
    return arg.find(';') == -1 and arg.find('|') == -1

def parse_values(params, defaults):
    """Parses a Values parameter which should have only two values separated by
    a comma. Used to override ON/OFF type messages.
    """
    try:
        split = params("Values").split(",")
        if len(split) != 2:
            return defaults
        else:
            return split
    except NoOptionError:
        return defaults

def get_sequential_params(params, name):
    """Gets a list of values from sequentially named parameters."""
    values = []
    i = 1
    done = False
    while not done:
        try:
            param = "{}{}".format(name, i)
            values.append(params(param))
            i += 1
        except NoOptionError:
            done = True
    return values

def get_sequential_param_pairs(params, name1, name2):
    """Returns a dict of two sets of sequentially named parameters using the
    value of name1 as the key and the value of name2 of the value.
    """
    one = get_sequential_params(params, name1)
    two = get_sequential_params(params, name2)
    if len(one) != len(two):
        raise ValueError("Unequal number of parameters for %s and %s ", name1,
                         name2)
    return dict(zip(one, two))

def is_toggle_cmd(msg):
    """Returns true it the input (msg) is equal
    to the string "TOGGLE" or is a ISO 8601 formatted date time
    """
    is_toggle = msg == "TOGGLE"
    # datetime from sensor_reporter RpiGpioSensor (e.g. 2021-10-24T16:23:41.500792)
    is_dt = len(msg) == 26 and msg[10] == "T"
    # datetime from openHAB (e.g. 2022-02-27T17:58:45.165491+0100)
    is_dt_timezone = len(msg) == 31 and msg[10] == "T"
    return is_toggle or is_dt or is_dt_timezone
