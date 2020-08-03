"""Utility functions of general use.

Functions:
    - set_log_level: Sets the logging level on the passed in logger to the level
    equivalent to the passed "Level" property in params.
"""
import logging
from configparser import NoOptionError

def set_log_level(params, logger):
    """Expects a params with a Level property. If there is no property the
    default level of INFO is used. Supports all the standard Python logging
    levels. Sets the level of the passed in logger based on the params Level
    property.
    """
    level = "INFO"
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

    logger.setLevel(levels.get(level, logging.NOTSET))
