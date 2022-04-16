"""Utility functions of general use.

Functions:
    - set_log_level: Sets the logging level on the passed in logger to the level
    equivalent to the passed "Level" property in params.
    - issage: returns False if the passed in ag contains unsafe characters to use
    on the command line.
"""
import logging

DEFAULT_SECTION = "DEFAULT"

def set_log_level(params, logger):
    """Expects a params with a Level property. If there is no property the
    default level of INFO is used. Supports all the standard Python logging
    levels. Sets the level of the passed in logger based on the params Level
    property.
    """
    level = params.get("Level")

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

def parse_values(caller, connections, defaults):
    """Parses the Values parameter which should be either
    a two string values formated as a list or
    a dictionary with connection sections containing
    a string list of two items
    Used to override ON/OFF type messages.

    Exprects:
    - caller: the object of the calling device,
              following vars from the caller are used:
                - dev_cfg: dictionary with the device specific config
                - log: the log instance of the device
                - connections: dictionary of the device connections
    - connections: dictionary of connector objects (in class sensor it's named 'publishers')
    - defaults: a list of two values which are used as defaults

    Returns: a dict containing the configured value pairs for each connection
    """
    values = caller.dev_cfg.get('Values', defaults)
    # warn if format is not supported
    if not isinstance(values, (list, dict)):
        values = defaults
        caller.log.warning("%s Values not in the expected form."
                           " Expected dictionary of connection names containing a list."
                           " Using default values instead: %s", caller.name, defaults)

    if isinstance(values, dict):
        value_dict = values
    else:
        value_dict = {}

    #add default section if not present
    if DEFAULT_SECTION not in value_dict:
        value_dict[DEFAULT_SECTION] = defaults if isinstance(values, dict) else values

    #at this point value_dict contains at least the DEFAULT section
    for (conn, values) in value_dict.items():
        #make sure connection names exist
        if conn not in connections and conn != DEFAULT_SECTION:
            caller.log.warning("%s Values parameter contains unknown connection!"
                         " Probably the name of the connection %s"
                         " is misspelled.",
                         caller.name, conn)
        if isinstance(values, list):
            #make sure only two items are present
            if len(values) == 2:
                #check type of list item, warn if boolean
                for item in values:
                    if isinstance(item, bool):
                        value_dict[DEFAULT_SECTION] = defaults
                        caller.log.warning("%s found boolean in Values."
                                           " Expected list of strings, use ' ' in config"
                                           " to mark strings."
                                           " Using default values instead: %s",
                                           caller.name, defaults)
                        break
            else:
                #warn if list is not 2 items long
                value_dict[DEFAULT_SECTION] = defaults
                caller.log.warning("%s Values are not in the expected form."
                           " Expected dictionary of connection names containing a list"
                           " with two items."
                           " Using default values instead: %s",
                           caller.name, defaults)
                break
    #at this point value_dict contains only valid connections and lists of strings
    return value_dict

def get_msg_from_values(values, state_on):
    """For sensors which implement custom values to send on state change,
    this function will generate the msg dict to push to self._send()
    so every connection will get the corresponding values

    Expects:
    - values: the value_dict which was returned by parse_values
    - state_on: the state of the sensor as boolean
                set to 'True' when sensor is 'on' or
                to send the first list item of values

    Returns: a dict with the state to publish for reach connection
    """
    #invert state so 'True' = 1 will yield the first item of the list (index = 0)
    state_on = not state_on
    result = {}

    for (conn, val) in values.items():
        result[conn] = val[state_on]

    return result

def get_sequential_params(dev_cfg, name):
    """creates a list of values from sequentially named parameters.

    Arguments:
    - dev_cfg: device configuration
    - name: Parameter name as String"""
    values = []
    i = 1
    done = False
    while not done:
        try:
            param = f"{name}{i}"
            values.append(dev_cfg[param])
            i += 1
        except KeyError:
            done = True
    return values

def get_dict_of_sequential_param__output(dev_cfg, name, output_name):
    """Returns a dict of sequentially named parameters and
    Output names generated acordingly

    Arguments:
    - dev_cfg: device configuration
    - name: Parameter name as String
    - output_name: the name to use for the connections output
    """
    one = get_sequential_params(dev_cfg, name)
    two = []
    for i in range(len(one)):
        two.append(f"{output_name}{i+1}")

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

def spread_default_parameters(config, dev_cfg):
    """takes parameters from the DEFAULT section
    and spread them to the dev_cfg if not present already

    config: the compleat configuration
    dev_cfg: the device specific configuration
    """
    def_cfg = config.get('DEFAULT')
    if def_cfg is None:
        return

    for (key, value) in def_cfg.items():
        if key not in dev_cfg:
            dev_cfg[key] = value

def verify_connections_layout(comm, log, name, triggers=None):
    """checks if the subdictionaries in the connections section
    are valid triggers

    comm: the communications dictionary will all connections
    log: the log instance of the device
    name: the name of the device
    triggers: a list of valid values for device triggers
    """
    for conn in comm.values():
        if isinstance(conn, dict):
            for (key, value) in conn.items():
                if isinstance(value, dict):
                    if not key in triggers:
                        log.warning("%s has unknown outputs '%s' in Connections."
                                    ' Valid outputs are: %s', name, key, triggers)
