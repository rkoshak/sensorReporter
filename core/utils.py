import logging
from configparser import NoOptionError

def set_log_level(params, logger):
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
