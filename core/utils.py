"""Utility functions of general use.

Functions:
    - set_log_level: Sets the logging level on the passed in logger to the level
    equivalent to the passed "Level" property in params.
    - issage: returns False if the passed in ag contains unsafe characters to use
    on the command line.
"""
import logging
import datetime
import colorsys
from enum import Enum, auto
from typing import Any, Union, Optional, Dict, List
# workaround circular import sensor <=> utils, import only file but not the method/object
from core import sensor
from core import connection

DEFAULT_SECTION = "DEFAULT"
# Constants for auto discover connections:
OUT = "$out"
IN = "$in"

# connection sub directory constants
CONF_ON_DISCONNECT = 'ConnectionOnDisconnect'
CONF_ON_RECONNECT = 'ConnectionOnReconnect'
CONF_SCHEDULER = 'ConnectionEnabledSchedule'

class ChanConst():
    """Constants used by configure_device_channel and homie_conn
    to define channel properties
    """
    DATATYPE = "Type"
    NAME = "FullName"
    UNIT = "Unit"
    SETTABLE = "Settable"
    FORMAT = "FormatOf"

class ChanType(Enum):
    """Datatypes supported by configure_device_channel
    """
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    STRING = auto()
    ENUM = auto()
    COLOR = auto()

def set_log_level(params:Dict[str, Any],
                  logger:logging.Logger) -> None:
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

def parse_values(caller:sensor.Sensor,
                 connections:Dict[str, Any],
                 defaults:List[str]) -> Dict[str, List[str]]:
    """Parses the Values parameter which should be either
    a two string values formated as a list or
    a dictionary with connection sections containing
    a string list of two items
    Used to override ON/OFF type messages.

    Expects:
    - caller: the object of the calling device,
              following vars from the caller are used:
                - dev_cfg: dictionary with the device specific config
                - log: the log instance of the device
                - connections: dictionary of the device connections
    - connections: dictionary of connector objects (in class sensor it's named 'publishers')
    - defaults: a list of two values which are used as defaults

    Returns: a dict containing the configured value pairs for each connection
    """
    values:Union[List[str],Dict[str,List[str]]] = caller.dev_cfg.get('Values', defaults)
    # warn if format is not supported
    if not isinstance(values, (list, dict)):
        values = defaults
        caller.log.warning("%s Values not in the expected form."
                           " Expected dictionary of connection names containing a list."
                           " Using default values instead: %s", caller.name, defaults)

    value_dict:Dict[str, List[str]] = {}
    if isinstance(values, dict):
        value_dict = values

    # add default section if not present
    if DEFAULT_SECTION not in value_dict:
        value_dict[DEFAULT_SECTION] = defaults if isinstance(values, dict) else values

    # at this point value_dict contains at least the DEFAULT section
    for (conn, values) in value_dict.items():
        # make sure connection names exist
        if conn not in connections and conn != DEFAULT_SECTION:
            caller.log.warning("%s Values parameter contains unknown connection!"
                         " Probably the name of the connection %s"
                         " is misspelled.",
                         caller.name, conn)
        if isinstance(values, list):
            # make sure only two items are present
            if len(values) == 2:
                # check type of list item, warn if boolean
                for item in values:
                    if not isinstance(item, str):
                        value_dict[DEFAULT_SECTION] = defaults
                        caller.log.warning("%s found: %s %s in Values."
                                           " Expected list of strings, use ' ' in config"
                                           " to mark strings."
                                           " Using default values instead: %s",
                                           caller.name, item, type(item), defaults)
                        break
            else:
                # warn if list is not 2 items long
                value_dict[DEFAULT_SECTION] = defaults
                caller.log.warning("%s Values are not in the expected form."
                           " Expected dictionary of connection names containing a list"
                           " with two items."
                           " Using default values instead: %s",
                           caller.name, defaults)
                break
    # at this point value_dict contains only valid connections and lists of strings
    return value_dict

def get_msg_from_values(values:Dict[str, List[str]],
                        state_on:bool) -> Dict[str, str]:
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

def is_toggle_cmd(msg:str) -> bool:
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

def verify_connections_layout(comm:Dict[str, Any],
                              log:logging.Logger,
                              name:str,
                              outputs:Optional[List[str]] = None) -> None:
    """
    Use this method at the end of the sensor initialization
    before calling configure_device_channel().
    Checks the YAML configuration to make sure the sub-dictionaries
    in the connections section are valid outputs

    comm:    the communications dictionary with all connections
    log:     the log instance of the device
    name:    the name of the device
    outputs: optional, a list of valid values for device outputs.
             If omitted, the function will ensure that the YAML
             configuration does not specify any output channels for the device.
             Expects the output_names used by a sensor as list e. g.:
             outputs = [output_name1, output_name2]
    """
    # In case outputs has the wrong data type
    if not isinstance(outputs, list):
        outputs = None
    # exclude sub-dictionaries used to configure the connection
    conn_conf = [CONF_ON_DISCONNECT, CONF_ON_RECONNECT, CONF_SCHEDULER]

    for conn in comm.values():
        if not isinstance(conn, dict):
            continue
        # loop thru all connections
        for (key, value) in conn.items():
            # loop thru sub items of the connections
            # if sub item is a dict we found a output channel
            # exclude sub-directories used to configure the connection
            if not isinstance(value, dict):
                continue
            if key in conn_conf:
                # Check data-type of VAL_TARGET_STATE = 'TargetState' expected 'str'
                target_val = value.get(connection.VAL_TARGET_STATE, '')
                if not isinstance(target_val, str):
                    log.warning("%s found non string value for '%s'."
                                " Expected string, use ' ' in config",
                                name, connection.VAL_TARGET_STATE)
                # continue if key in conn_conf, no matter if warning was printed
                continue
            if outputs is None:
                # handle case where outputs is not specified
                log.warning("%s has unexpected outputs '%s' in Connections."
                            ' No outputs are allowed', name, key)
                continue
            # check if sub-dictionary is specified as outputs
            if not key in outputs:
                log.warning("%s has unknown outputs '%s' in Connections."
                            ' Valid outputs are: %s', name, key, outputs)


def configure_device_channel(comm:Dict[str, Any], *,
                            is_output:bool,
                            output_name:Optional[str] = None,
                            datatype:ChanType = ChanType.STRING,
                            unit:Optional[str] = None,
                            name:Optional[str] = None,
                            restrictions:Optional[str] = None) -> None:
    """
    Use this method at the end of the sensor/actuator initialization,
    it sets default values inside the connections section
    so that a connector which supports auto-discover, e. g. homie_conn,
    can register the device correctly.

    Call this method once for each output the sensor has, to register all output channels.
    For actuators, only one input and output is currently supported, so one call to
    this method is sufficient.
    After calling this method, self._register() must be called, see the example below.

    Parameters:
    - comm:         the connections dictionary of the device
    - is_output:    to select if a output or a input should be configured.
                    Set to true for a sensor and false for an actuator

    Optional Parameters:
    - output_name:  the name used to publish messages by _send() and _publish().
                    For sensors: specify the name of the output channel if more than one is used
                    otherweise don't use this parameter.
                    For actuators: don't use this parameter
    - datatype:     the type of the data the device will be published or received:
                    [STRING, INTEGER, FLOAT, BOOLEAN, ENUM, COLOR]
                    use class ChanType, e. g. ChanType.INTEGER
    - unit:         the unit in which the sensor data is published:
                    [°C, °F, °, L, gal, V, W, A, %, m, ft, Pa, psi, #]
                    e. g. unit = "Pa"
    - name:         the full name / description of the input/output
                    this is visible on the connected server e. g. openHAB
    - restrictions: set allowed values for channel
                    for a numeric range e. g. -3:24
                    for possible values for datatype ENUM
                    as comma separated list e.g. 'val1,val2,val3'
                    the homie convention named this "format"

    It is required to write the parameter name out, when calling this method
    ==Example from RpiGpioActuator==
    configure_device_channel(self.comm, is_output=False,
                             name="set digital output", datatype=ChanType.ENUM,
                             restrictions="ON,OFF,TOGGLE")
    self._register(self.comm, None)

    ==Example 2 from heartbeat (sensor)==
    configure_device_channel(self.comm, is_output=True, output_name=OUT_NUM,
                                 datatype=ChanType.INTEGER, name="uptime in milliseconds")
    configure_device_channel(self.comm, is_output=True, output_name=OUT_STRING,
                             name="uptime in days, hours:min:sec")
    self._register(self.comm)
    """

    for comm_conn in comm.values():
        if output_name:
            if output_name not in comm_conn:
                comm_conn[output_name] = {}
            local_comm = comm_conn[output_name]
        else:
            local_comm = comm_conn

        subdict = OUT if is_output else IN

        if subdict not in local_comm:
            local_comm[subdict] = {}

        sub = local_comm[subdict]

        if ChanConst.DATATYPE not in sub:
            sub[ChanConst.DATATYPE] = datatype

        if unit:
            if ChanConst.UNIT not in sub:
                sub[ChanConst.UNIT] = unit

        if name:
            if ChanConst.NAME not in sub:
                sub[ChanConst.NAME] = name

        if restrictions:
            if ChanConst.FORMAT not in sub:
                sub[ChanConst.FORMAT] = restrictions

        if not is_output:
            if ChanConst.SETTABLE not in sub:
                sub[ChanConst.SETTABLE] = True

class Debounce():
    """ Checks the time difference between two  sequential events
        and checks if the debounce time is already over
    """

    def __init__(self, dev_cfg:Dict[str, Any],
                 default_debounce_time:float) -> None:
        """Init and read device configuration

            Parameters:
            - "dev_cfg"                  : 'dev_cfg' instance of the calling sensor / actuator
            - "default_debounce_time"    : time in seconds to use as default value for
                                           device config item 'ToggleDebounce' (float)
                                           recommended value 0.15 (seconds)

            The following optional parameters are read from device config:
                - "ToggleDebounce"       : The interval in seconds during which repeated
                                           toggle commands are ignored
        """
        # store default debounce time
        self.debounce_time = float(dev_cfg.get("ToggleDebounce", default_debounce_time))
        self.last_time = datetime.datetime.fromordinal(1)

    def is_within_debounce_time(self) -> bool:
        """Checks the time difference between two  sequential events
           and checks if the debounce time is already over

           Returns True if the last call to this method is within the debounce time
           otherways it returns false
        """
        # remember time for toggle debounce
        time_now = datetime.datetime.now()
        seconds_since_toggle = (time_now - self.last_time).total_seconds()
        self.last_time = time_now
        if seconds_since_toggle < self.debounce_time:
            return True
        return False

class ColorHSV():
    ''' Stores HSV color values. Hue can range from 0 (= off) to 360 (= full brightness),
        Saturation and Value can range from 0 (= off) to 100 (= full brightness).
        Allows read access to individual values and a dictionary of all RGBW values.
        Exposed property to set and get color in HSV format
        e. g. green with full brightness =  '120,100,100'
    '''

    # Constants
    C_RED = "Red"
    C_GREEN = "Green"
    C_BLUE = "Blue"
    C_WHITE = "White"
    C_RGBW_ARRAY = [C_RED, C_GREEN, C_BLUE, C_WHITE]
    C_HUE = 'Hue'
    C_SAT = 'Saturation'
    C_VAL = 'Value'

    def __init__(self,
                 RGBW_dict:Dict[str, int],
                 use_white_channel:bool) -> None:
        ''' Initializes colors to a given value (range 0 to 100)
            Parameters:
                * RGBW_dict             Dictionary of color : value pairs that define
                                        the initial value for the colors.
                                        RGBW_dict = {
                                            C_RED   : red_value,
                                            C_GREEN : green_value,
                                            C_BLUE  : blue_value,
                                            C_WHITE : white_value
                                            }
                                        Range: 0 (= off) to 100 (= full brightness)
                * use_white_channel     Boolean, if true the 'color_hsv_str' property assumes
                                        a white LED is present.
                                        So HSV color 0,0,100 (no saturation) will be
                                        converted to RGBW {red: 0, green: 0, blue:0, white:100}
                                        If false: HSV color 0,0,100 will result in RGBW
                                        {red: 100, green: 100, blue:100, white:0}
        '''
        self._hsv = {
            self.C_HUE : 0,
            self.C_SAT : 0,
            self.C_VAL : 0
            }
        self.use_white_ch = use_white_channel

        if RGBW_dict.get(self.C_WHITE, 0) != 0:
            RGBW_dict[self.C_RED] = 0
            RGBW_dict[self.C_GREEN]= 0
            RGBW_dict[self.C_BLUE] = 0

        self.rgbw_dict = RGBW_dict

    def __eq__(self,
               other_obj:object) -> bool:
        ''' own implementation of compare equality to simplify code using this class
        '''
        if not isinstance(other_obj, ColorHSV):
            # only compare to ColorHSV class
            return NotImplemented
        return self._hsv == other_obj.hsv_dict

    @property
    def rgbw_dict(self) -> Dict[str, int]:
        ''' Get or set color as RGBW dictionary
            RGBW_dict = {
                C_RED   : red_value,
                C_GREEN : green_value,
                C_BLUE  : blue_value,
                C_WHITE : white_value
                        }
            If colors are not present in the dictionary when writing
            to this property the value is assumed to be 0
        '''
        # create empty RGBW dict
        rgbw_dict = {}
        for key in self.C_RGBW_ARRAY:
            rgbw_dict[key] = 0

        # Check if saturation (hsv_array[1]) equals 0 then set RGB = 0 w = value (hsv_array)
        if self._hsv[self.C_SAT] == 0 and self.use_white_ch:
            # set white channel to saturation
            rgbw_dict[self.C_WHITE] = self._hsv[self.C_VAL]
        else:
            # Convert HSV color to RGB color tuple
            color_rgb = colorsys.hsv_to_rgb(self._hsv[self.C_HUE]/360,
                                            self._hsv[self.C_SAT]/100,
                                            self._hsv[self.C_VAL]/100)
            # Set white channel to 0
            color_rgbw = color_rgb + (0,)
            # store converted values
            for (key, val) in zip(self.C_RGBW_ARRAY, color_rgbw):
                rgbw_dict[key] = round(val * 100)

        return rgbw_dict

    @rgbw_dict.setter
    def rgbw_dict(self,
                  rgbw_dict:Dict[str, int]) -> None:
        # Build HSV color CSV array
        if rgbw_dict.get(self.C_WHITE, 0) == 0:
            # If white is not set use RGB values
            # Normalize RGB values and calculate HSV color
            hsv_tuple = colorsys.rgb_to_hsv(rgbw_dict.get(self.C_RED, 0)/100,
                                            rgbw_dict.get(self.C_GREEN, 0)/100,
                                            rgbw_dict.get(self.C_BLUE, 0)/100)
            # scale hsv_tuple and build array
            hsv_array = [hsv_tuple[0] * 360,
                         hsv_tuple[1] * 100,
                         hsv_tuple[2] * 100]
            if hsv_array[1] == 0:
                # Note: HSV 0,0,x seems to be out of range for openHAB item
                # and HSV 1,0,0 doesn't work for homie connection using 2,0,x instead
                hsv_array[0] = 2
        else:
            # Build HSV color array for case white color is set
            # Note: 0,0,x seems to be out of range for openHAB using 1,0,x instead
            hsv_array = [2,0,rgbw_dict[self.C_WHITE]]
        # store result as integer to get rid of floating point numbers
        self._hsv[self.C_HUE] = int(hsv_array[0])
        self._hsv[self.C_SAT] = int(hsv_array[1])
        self._hsv[self.C_VAL] = int(hsv_array[2])

    @property
    def hsv_dict(self) -> Dict[str, int]:
        ''' Get the internal HSV dictionary
        '''
        return self._hsv

    @property
    def color_hsv_str(self) -> str:
        ''' Get or set the color in HSV format
            as comma separated value string without spaces: hue,saturation,value
            E. g. pure red in full brightness = '0,100,100'
        '''
        # build hsv_color_str
        hsv_color_str = ( f'{int(self._hsv[self.C_HUE])},'
                          f'{int(self._hsv[self.C_SAT])},'
                          f'{int(self._hsv[self.C_VAL])}' )

        return hsv_color_str

    @color_hsv_str.setter
    def color_hsv_str(self,
                      hsv_str:str) -> None:
        hsv_array = []
        # We expect a string with 3 values: hue,saturation,value
        # Split and convert them to integer
        for val in hsv_str.split(","):
            hsv_array.append(int(val))

        self._hsv[self.C_HUE] = hsv_array[0]
        self._hsv[self.C_SAT] = hsv_array[1]
        self._hsv[self.C_VAL] = hsv_array[2]

    def get_hsv(self,
                param:str) -> int:
        ''' Returns the selected 'parameter' as an integer (range 0 to 100/360).
            Raises an error if the specified parameter is not in the internal HSV color dictionary.
            Parameter:
                * param    String, one of "Hue", "Saturation", "Value"
        '''
        if param in self._hsv:
            return self._hsv[param]
        raise ValueError(f"Function 'get_hsv()' parameter 'param' has unknown value: {param}")

    def set_hsv(self,
                param:str,
                value:int) -> None:
        ''' Sets the selected 'param' as in integer (range 0 to 100/360).
            Raises an error if the specified param is not in the internal HSV color dictionary.
            Parameter:
                * param    String, one of "Hue", "Saturation", "Value"
        '''
        if param in self._hsv:
            if param == self.C_HUE and (value < 0 or value > 360):
                raise ValueError(f"Function 'set_hsv()' parameter 'value' \
                                out of range should be 0 to 360 is: {value}")
            if param != self.C_HUE and (value < 0 or value > 100):
                raise ValueError(f"Function 'set_hsv()' parameter 'value' \
                                out of range should be 0 to 100 is: {value}")
            self._hsv[param] = value
        else:
            raise ValueError(f"Function 'set_hsv()' parameter 'param' has unknown value: {param}")

