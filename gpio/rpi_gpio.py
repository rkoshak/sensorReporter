# Copyright 2020 Richard Koshak
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Contains RPI GPIO sensors, actuators, and connections.

Classes:
    - RpiGpioSensor: Reports on the state of a GPIO Pin.
    - RpiGpioActuator: Sets a pin to HIGH or LOW on command.
"""
from time import sleep
from distutils.util import strtobool
from logging import Logger
from typing import Any, Optional, Union, Dict
import datetime
import yaml
import lgpio            # https://abyz.me.uk/lg/py_lgpio.html
from core.sensor import Sensor
from core.actuator import Actuator
from core import utils
from core import connection

# connection dict constants
OUT_SWITCH = "Switch"
OUT_SHORT_PRESS = "ShortButtonPress"
OUT_LONG_PRESS = "LongButtonPress"

def check_lgpio_ver(log:Logger) -> None:
    """ check lgpio version
        raise warning if version is below 0.2.2.0
    """
    if lgpio.LGPIO_PY_VERSION < 0x00020200:
        log.warn("Found module %s, for versions below 0.2.2.0 debounce might not work!",
                 lgpio.get_module_version())

def highlow_to_str(output:int) -> str:
    """    Converts (lgpio.)HIGH (=1) and LOW (=0) to the corresponding string

           Parameter: - "output": the GPIO constant (HIGH or LOW)

           Returns string HIGH/LOW
    """
    if output:
        return "HIGH"

    return "LOW"

class RpiGpioSensor(Sensor):
    """Publishes the current state of a configured GPIO pin."""

    def __init__(self,
                 publishers:Dict[str, connection.Connection],
                 dev_cfg:Dict[str, Any]) -> None:
        """ Initializes the connection to the GPIO pin and if "EventDetection"
            if defined and valid, will subscribe for events. If missing, than it
            requires the "Poll" parameter be defined and > 0. By default it will
            publish CLOSED/OPEN for 0/1 which can be overridden by the "Values" which
            should be a comma separated list of two parameters, the first one is
            CLOSED and second one is OPEN.

            Parameters:
                - "GpioChip"      : The number of the GPIO chip to use
                - "Pin"           : the GPIO pin in BCM numbering
                - "Values"        : Alternative values to publish for 0 and 1, defaults to
                                    OPEN and CLOSED for 0 and 1 respectively.
                - "PUD"           : Pull up or down setting, if "UP" uses PULL_UP, all other
                                    values result in PULL_DOWN.
                - "EventDetection": when set instead of depending on sensor_reporter
                                    to poll it will relay on the event detection built into the GPIO
                                    library. Valid values are "RISING", "FALLING" and "BOTH".
                                    When not defined "Poll" must be set to a positive value.
        """
        super().__init__(publishers, dev_cfg)

        check_lgpio_ver(self.log)

        self.pin = int(dev_cfg["Pin"])
        gpio_chip = int(dev_cfg["GpioChip"])

        # Allow users to override the 0/1 pin values.
        self.values = utils.parse_values(self, self.publishers, ["OPEN", "CLOSED"])

        self.pud:int = lgpio.SET_PULL_UP if dev_cfg.get("PUD") == "UP" else lgpio.SET_PULL_DOWN
        try:
            self.chip_handle:int = lgpio.gpiochip_open(gpio_chip)
        except lgpio.error as err:
            self.log.error("%s could not setup GPIO chip %d. "
                           "Make sure the chip number is correct. Error Message: %s",
                           self.name, gpio_chip,err)

        # Set up event detection.
        try:
            event_detection:str = dev_cfg["EventDetection"]
            event_map:Dict[str, int] = {"RISING": lgpio.RISING_EDGE,
                                        "FALLING": lgpio.FALLING_EDGE,
                                        "BOTH": lgpio.BOTH_EDGES}
            if event_detection not in event_map:
                self.log.error("Invalid event detection specified: %s, one of RISING,"
                               " FALLING, BOTH or NONE are the only allowed values. "
                               "Defaulting to NONE",
                               event_detection)
                event_detection = "NONE"
        except KeyError:
            self.log.info("No event detection specified, falling back to polling "
                          "with interval %s", self.poll)
            event_detection = "NONE"

        try:
            if event_detection == "NONE":
                lgpio.gpio_claim_input(self.chip_handle, self.pin, self.pud)
            else:
                # setup event detection
                lgpio.gpio_claim_alert(self.chip_handle, self.pin,
                                       event_map[event_detection], self.pud)
                lgpio.callback(self.chip_handle, self.pin,
                               event_map[event_detection], self.gpio_event_cbf)
        except (lgpio.error, TypeError) as err:
            self.log.error("%s could not setup GPIO chip %d, pin %d. "
                           "Make sure the pin number is correct. Error Message: %s",
                           self.name, gpio_chip, self.pin,err)

        self.state:int = lgpio.gpio_read(self.chip_handle, self.pin)

        if self.poll < 0 and event_detection == "NONE":
            raise ValueError("Event detection is NONE but polling is OFF")
        if self.poll > 0 and event_detection != "NONE":
            raise ValueError(f'Event detection is {event_detection} but polling is {self.poll}')

        self.btn = ButtonPressCfg(dev_cfg, self)

        # verify that defined output channels in Connections section are valid!
        utils.verify_connections_layout(self.comm, self.log, self.name,
                                        [OUT_SWITCH, OUT_SHORT_PRESS, OUT_LONG_PRESS])

        self.log.info("Configured RpiGpioSensor %s: chip %d, pin %d with PUD %s",
                      self.name, gpio_chip, self.pin,
                      "UP" if self.pud == lgpio.SET_PULL_UP else "DOWN")
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))
        self.log.debug("%s configured values: \n%s",
                       self.name, yaml.dump(self.values))

        self.publish_state()

        # configure_output for homie etc. after debug output, so self.comm is clean
        utils.configure_device_channel(self.comm, is_output=True, output_name=OUT_SWITCH,
                                       name="switch state")
        utils.configure_device_channel(self.comm, is_output=True, output_name=OUT_SHORT_PRESS,
                                       name="timestamp of last short press")
        utils.configure_device_channel(self.comm, is_output=True, output_name=OUT_LONG_PRESS,
                                       name="timestamp of last long press")
        self._register(self.comm)

    def check_state(self) -> None:
        """ Checks the current state of the pin and forwards it
            to gpio_event_cbf(). When polling this method gets called
            on each poll.
        """
        value:int = lgpio.gpio_read(self.chip_handle, self.pin)
        self.gpio_event_cbf(None, self.pin, value, None)

    def gpio_event_cbf(self,
                       _chip:Optional[int],
                       gpio:int,
                       level:int,
                       _timestamp:Optional[int]) -> None:
        """ Receives the current gpio pin state (level)
            and if it's different from the
            last state publishes it.
            With event detection this method gets called
            when the GPIO pin changed states (via lgpio callback).

            Parameters:
            _chip        : The GPIO-Chip of the Pin that changed (unused)
            gpio         : The GPIO-Pin that has changed
            level        : The new state of the GPIO-Pin one of:
                            0 - LOW
                            1 - HIGH
                            2 - watchdog timeout
            _timestamp    : Time stamp of the change event (unused)
        """
        # NOTE: Events triggered by Event_dectection only RISING / FALLING won't
        #       get processed since the level doesn't change.
        #       08.04.2024 - Tested implementation for only RISING / FALLING edge
        #       but this will produce a lot of double events from one button press,
        #       even with debounce.
        # Make sure the gpio level has changed and no lgpio watchdog timeout has occurred
        if level not in (self.state, lgpio.TIMEOUT):
            self.log.info("%s Pin %s changed from %s to %s (= %s)",
                          self.name, gpio, self.state,
                          level, self.values[utils.DEFAULT_SECTION][not level])
            self.state = level
            self.publish_state()
            self.btn.check_button_press(self)

    def publish_state(self) -> None:
        """ Publishes the current state of the pin."""
        msg = utils.get_msg_from_values(self.values, self.state == lgpio.HIGH)
        self._send(msg, self.comm, OUT_SWITCH)

    def publish_button_state(self,
                             is_short_press:bool) -> None:
        """ Send update to destination depending on button press duration"""
        curr_time_iso = datetime.datetime.now().isoformat()
        if is_short_press:
            self._send(curr_time_iso, self.comm, OUT_SHORT_PRESS)
        else:
            self._send(curr_time_iso, self.comm, OUT_LONG_PRESS)

    def cleanup(self) -> None:
        """ Disconnects from the GPIO subsystem."""
        self.log.debug("%s cleaning up GPIO inputs, invoked via Pin %d",
                       self.name, self.pin)
        lgpio.gpio_free(self.chip_handle, self.pin)
        lgpio.gpiochip_close(self.chip_handle)

class ButtonPressCfg():
    """ Stores all button related parameters """
    def __init__(self,
                 dev_cfg:Dict[str, Any],
                 caller:RpiGpioSensor) -> None:
        """ Read optional button press  related parameters from the config

            Parameters:
            - dev_cfg : the dictionary that stores the config values for a sensor
            - caller     : the object of the calling sensor
        """
        self.high_time:Optional[datetime.datetime] = None
        # Expect threshold in seconds
        # Set default for Short_Press-Threshold to 2ms,
        # lgpio edge detection reacts very sensitive to bouncy buttons
        self.short_press_time = float(dev_cfg.get("Short_Press-Threshold", 0.002))
        self.long_press_time = float(dev_cfg.get("Long_Press-Threshold",0))
        try:
            # set lgpio debounce to half Short_Press-Threshold and convert seconds to microseconds
            lgpio.gpio_set_debounce_micros(caller.chip_handle, caller.pin,
                                           int(self.short_press_time / 2 * 1000000))
        except (lgpio.error, TypeError) as err:
            caller.log.error("%s could not setup GPIO debounce for pin %d. "
                           "Make sure the pin number is correct. Error Message: %s",
                           caller.name, caller.pin, err)
        try:
            self.state_when_pressed = lgpio.LOW if dev_cfg["Btn_Pressed_State"]=="LOW" \
                                        else lgpio.HIGH
        except KeyError:
            # if value not in the config, determined it from PUD
            self.state_when_pressed = lgpio.LOW if caller.pud == lgpio.SET_PULL_UP else lgpio.HIGH

        caller.log.info('%s configured button press events, with short press threshold %s, '
                        'long press threshold %s and pressed state %s',
                        caller.name, self.short_press_time, self.long_press_time,
                        highlow_to_str(self.state_when_pressed))

    def check_button_press(self,
                           caller:RpiGpioSensor) -> None:
        """ Checks the duration the contact was closed and
            rises the event configured with that duration

            Parameter:
                 - caller : the object of the caller
                            so self.log and self.publish_button_state can be accessed
         """
        # get time during button was closed
        if caller.state == self.state_when_pressed:
            self.high_time = datetime.datetime.now()
        elif self.high_time is None:
            caller.log.warning("%s expected contact closed before release."
                               " 'Btn_Pressed_State' is probably configured wrong"
                               " for Pin: %s", caller.name, caller.pin)
        else:
            time_delta_seconds = (datetime.datetime.now() - self.high_time).total_seconds()
            if time_delta_seconds > self.short_press_time:
                if self.long_press_time != 0 and time_delta_seconds > self.long_press_time:
                    caller.log.info("%s long button press occurred on Pin %s"
                                  " was pressed for %s seconds",
                                  caller.name, caller.pin, time_delta_seconds)
                    caller.publish_button_state(is_short_press = False)
                else:
                    caller.log.info("%s short button press occurred on Pin %s"
                                  " was pressed for %s seconds",
                                  caller.name, caller.pin, time_delta_seconds)
                    caller.publish_button_state(is_short_press = True)

class RpiGpioActuator(Actuator):
    """ Allows for setting a GPIO pin to high or low on command.
        Also supports toggling.
    """

    def __init__(self,
                 connections:Dict[str, connection.Connection],
                 dev_cfg:Dict[str, Any]) -> None:
        """ Initializes the GPIO subsystem and sets the pin to the InitialState.
            If InitialState is not provided in params it defaults to lgpio.HIGH.
            If "SimulateButton" is defined on any message will result in the pin
            being set to HIGH for half a second and then back to LOW.

            Parameters:
                - "GpioChip"      : The number of the GPIO chip to use
                - "Pin"           : The GPIO pin in BCM numbering
                - "InitialState"  : The pin state to set when coming online,
                                    defaults to "LOW".
                - "SimulateButton": Optional parameter that when set to "True" causes any
                                    message received to result in setting the pin to HIGH, sleep for
                                    half a second, then back to LOW.
            Parameters included in external classes:
                - "ToggleDebounce": The interval in seconds during which repeated
                                    toggle commands are ignored (default 0.15 seconds)
        """
        super().__init__(connections, dev_cfg)

        self.pin = int(dev_cfg["Pin"])
        gpio_chip = int(dev_cfg["GpioChip"])
        self.invert:bool = dev_cfg.get("InvertOut", False)

        initial_state:Union[bool, str] = dev_cfg.get("InitialState", False)
        # ymal.load will convert ON / OFF to True / False
        # Introduced HIGH / LOW since ON / OFF is very confusing when setting the pin state
        state_map = {True  : lgpio.HIGH, False : lgpio.LOW,
                     'HIGH': lgpio.HIGH, 'LOW' : lgpio.LOW}
        self.init_state:int = state_map.get(initial_state, lgpio.LOW)

        try:
            self.chip_handle:int = lgpio.gpiochip_open(gpio_chip)
            lgpio.gpio_claim_output(self.chip_handle, self.pin, self.init_state)
        except ValueError as err:
            self.log.error("%s could not setup GPIO Pin %d . "
                           "Make sure the pin number is correct. Error Message: %s",
                           self.name, self.pin, err)

        try:
            self.sim_button:bool = dev_cfg["SimulateButton"]
        except KeyError:
            self.sim_button = dev_cfg.get("Toggle", False)

        # Init debounce with 0.15s default
        self.debounce = utils.Debounce(dev_cfg, default_debounce_time = 0.15)

        # remember the current output state
        if self.sim_button:
            self.current_state:Optional[int] = None
        else:
            if self.invert:
                self.current_state = not self.init_state
            else:
                self.current_state = self.init_state

        self.log.info("Configued RpiGpioActuator %s: pin %d on with SimulateButton %s",
                      self.name, self.pin, self.sim_button)
        self.log.debug("%s has following configured connections: \n%s",
                       self.name, yaml.dump(self.comm))

        # publish initial state back to remote connections
        self.publish_actuator_state()

        utils.configure_device_channel(self.comm, is_output=False,
                                       name="set digital output", datatype=utils.ChanType.ENUM,
                                       restrictions="ON,OFF,TOGGLE")
        # The actuator gets registered twice, at core-actuator and here
        # currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self,
                   msg:str) -> None:
        """ Called when the actuator receives a message. If SimulateButton is not enabled
            sets the pin to HIGH if the message is ON and LOW if the message is OFF.
        """
        # ignore command echo which occurs with multiple connections:
        # do nothing when the command (msg) equals the current state,
        # ignore this on SimulateButton mode
        if not self.sim_button:
            if msg in ("ON", "OFF"):
                if self.current_state == strtobool(msg):
                    self.log.info("%s received command %s"
                                  " which is equal to current output state. Ignoring command!",
                                  self.name, msg)
                    return
            elif utils.is_toggle_cmd(msg):
                if self.debounce.is_within_debounce_time():
                    # filter close toggle commands to make sure no double switching occurs
                    self.log.info("%s received toggle command %s"
                                  " within debounce time. Ignoring command!",
                                  self.name, msg)
                    return
                msg = "TOGGLE"

        self.log.info("%s received command %s, SimulateButton = %s, Invert = %s, Pin = %d",
                      self.name, msg, self.sim_button, self.invert, self.pin)

        # SimulateButton on then off.
        if self.sim_button:
            self.log.info("%s toggles pin %s, %s to %s",
                          self.name, self.pin,
                          highlow_to_str(self.init_state),
                          highlow_to_str(not self.init_state))
            lgpio.gpio_write(self.chip_handle, self.pin, int(not self.init_state))
            # "sleep" will block a local connection and therefore
            # distort the time detection of button press event's
            sleep(.5)
            self.log.info("%s toggles pin %s, %s to %s",
                          self.name, self.pin,
                          highlow_to_str(not self.init_state),
                          highlow_to_str(self.init_state))
            lgpio.gpio_write(self.chip_handle, self.pin, self.init_state)

        # Turn ON/OFF based on the message.
        else:
            out = None
            if msg == "ON":
                out = lgpio.HIGH
            elif msg == "OFF":
                out = lgpio.LOW
            elif msg == "TOGGLE":
                out = int(not self.current_state)

            if out is None:
                self.log.error("%s bad command %s", self.name, msg)
            else:
                self.current_state = out
                if self.invert:
                    out = int(not out)

                self.log.info("%s set pin %d to %s",
                              self.name, self.pin,
                              highlow_to_str(out))
                lgpio.gpio_write(self.chip_handle, self.pin, out)

                # publish own state back to remote connections
                self.publish_actuator_state()

    def publish_actuator_state(self) -> None:
        """Publishes the current state of the actuator."""
        msg:str = "ON" if self.current_state else "OFF"
        self._publish(msg, self.comm)

    def cleanup(self) -> None:
        """Disconnects from the GPIO subsystem."""
        self.log.debug("%s cleaning up GPIO outputs, invoked via Pin %d",
                       self.name, self.pin)
        lgpio.gpio_free(self.chip_handle, self.pin)
        lgpio.gpiochip_close(self.chip_handle)
