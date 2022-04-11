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
import datetime
import yaml
from RPi import GPIO
from core.sensor import Sensor
from core.actuator import Actuator
from core.utils import parse_values, is_toggle_cmd, verify_connections_layout

#constants
OUT_SWITCH = "Switch"
OUT_SHORT_PRESS = "ShortButtonPress"
OUT_LONG_PRESS = "LongButtonPress"

def set_gpio_mode(dev_cfg, log):
    """Set GPIO mode (BCM or BOARD) for all Sensors and Actuators
    put a Warning if it was changed or set multible times
    Parameters:
        - params : the lamda function that stores the config values for a sensor
        - log    : the self.log instance of the calling sensor
    """
    gpio_mode = GPIO.BOARD if dev_cfg.get("PinNumbering") == "BOARD" else GPIO.BCM

    try:
        GPIO.setmode(gpio_mode)
    except ValueError:
        log.error("GPIO PinNumbering was set differently before"
                    " make sure is is only set in the [DEFAULT] section.")
        return "Err: not set"
    return "BCM" if gpio_mode == GPIO.BCM else "BOARD"

def highlow_to_str(output):
    """Converts (GPIO.)HIGH (=1) and LOW (=0) to the corresponding string

    Parameter: - "output": the GPIO constant (HIGH or LOW)

    Returns string HIGH/LOW
    """
    if output:
        return "HIGH"

    return "LOW"

class RpiGpioSensor(Sensor):
    """Publishes the current state of a configured GPIO pin."""

    def __init__(self, publishers, dev_cfg):
        """Initializes the connection to the GPIO pin and if "EventDetection"
        if defined and valid, will subscibe fo events. If missing, than it
        requires the "Poll" parameter be defined and > 0. By default it will
        publish CLOSED/OPEN for 0/1 which can be overridden by the "Values" which
        should be a comma separated list of two paameters, the first one is
        CLOSED and second one is OPEN.

        Parameters:
            - "Pin": the IO pin in BCM/BOARD numbering
            - "Values": Alternative values to publish for 0 and 1, defaults to
            CLOSED and OPEN for 0 and 1 respectively.
            - "PUD": Pull up or down setting, if "UP" uses PULL_UP, all other
            values result in PULL_DOWN.
            - "EventDetection": when set instead of depending on sensor_reporter
            to poll it will reliy on the event detection built into the GPIO
            library. Valid values are "RISING", "FALLING" and "BOTH". When not
            defined "Poll" must be set to a positive value.
        """
        super().__init__(publishers, dev_cfg)

        self.gpio_mode = set_gpio_mode(dev_cfg, self.log)

        self.pin = int(dev_cfg["Pin"])

        # Allow users to override the 0/1 pin values.
        #TODO send warning if values are of type boolean
        self.values = parse_values(dev_cfg, ["OPEN", "CLOSED"])

        self.log.debug("%s configured %s for CLOSED and %s for OPEN",
                       self.name, self.values[1], self.values[0])

        pud = GPIO.PUD_UP if dev_cfg["PUD"] == "UP" else GPIO.PUD_DOWN
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)
        except ValueError as err:
            self.log.error("%s could not setup GPIO Pin %d (%s). "
                           "Make sure the pin number is correct. Error Message: %s",
                           self.name, self.pin, self.gpio_mode, err)

        # Set up event detection.
        try:
            event_detection = dev_cfg["EventDetection"]
            event_map = {"RISING": GPIO.RISING, "FALLING": GPIO.FALLING, "BOTH": GPIO.BOTH}
            if event_detection not in event_map:
                self.log.error("Invalid event detection specified: %s, one of RISING,"
                               " FALLING, BOTH or NONE are the only allowed values. "
                               "Defaulting to NONE",
                               event_detection)
                event_detection = "NONE"
        except KeyError:
            self.log.info("No event detection specified, falling back to polling")
            event_detection = "NONE"

        if event_detection != "NONE":
            GPIO.add_event_detect(self.pin, event_map[event_detection],
                                  callback=lambda channel: self.check_state())

        self.state = GPIO.input(self.pin)

        if self.poll < 0 and event_detection == "NONE":
            raise ValueError("Event detection is NONE but polling is OFF")
        if self.poll > 0 and event_detection != "NONE":
            raise ValueError("Event detection is {} but polling is {}"
                             .format(event_detection, self.poll))

        self.btn = ButtonPressCfg(dev_cfg, self)

        #verify that defined Triggers in Connections section are valid!
        verify_connections_layout(self.comm, self.log, self.name,
                                  [OUT_SWITCH, OUT_SHORT_PRESS, OUT_LONG_PRESS])

        self.log.info("Configued RpiGpioSensor %s: pin %d (%s) with PUD %s",
                      self.name, self.pin, self.gpio_mode,
                      "UP" if pud == GPIO.PUD_UP else "DOWN")
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        self.publish_state()

    def check_state(self):
        """Checks the current state of the pin and if it's different from the
        last state publishes it. With event detection this method gets called
        when the GPIO pin changed states. When polling this method gets called
        on each poll.
        """
        value = GPIO.input(self.pin)
        if value != self.state:
            self.log.info("%s Pin %s (%s) changed from %s to %s (= %s)",
                          self.name, self.pin, self.gpio_mode, self.state,
                          value, self.values[not value])
            self.state = value
            self.publish_state()
            self.btn.check_button_press(self)

    def publish_state(self):
        """Publishes the current state of the pin."""
        msg = self.values[0] if self.state == GPIO.HIGH else self.values[1]
        self._send(msg, self.comm, OUT_SWITCH)

    def publish_button_state(self, is_short_press):
        """send update to destination depending on button press duration"""
        curr_time_iso = datetime.datetime.now().isoformat()
        if is_short_press:
            self._send(curr_time_iso, self.comm, OUT_SHORT_PRESS)
        else:
            self._send(curr_time_iso, self.comm, OUT_LONG_PRESS)

    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        self.log.debug("%s cleaning up GPIO inputs, invoked via Pin %d (%s)",
                       self.name, self.pin, self.gpio_mode)
        GPIO.remove_event_detect(self.pin)
        # make sure cleanup runs only once
        if GPIO.getmode() is not None:
            GPIO.cleanup()

class ButtonPressCfg():
    """ stores all button related parameters
    """
    def __init__(self, dev_cfg, caller):
        """ read optional button press  related parametes from the config

            Parameters:
            - dev_cfg : the dictionary that stores the config values for a sensor
            - caller     : the objetc of the calling sensor
        """
        self.high_time = None
        #expect threshold in seconds
        self.short_press_time = float(dev_cfg.get("Short_Press-Threshold", 0))
        self.long_press_time = float(dev_cfg.get("Long_Press-Threshold",0))

        try:
            self.state_when_pressed = GPIO.LOW if dev_cfg["Btn_Pressed_State"]=="LOW" else GPIO.HIGH
        except KeyError:
            #if value not in the config, determind it from PUD
            self.state_when_pressed = GPIO.LOW if caller.pud == GPIO.PUD_UP else GPIO.HIGH

        caller.log.info('%s configued button press events, with short press threshold %s, '
                        'long press threshold %s and pressed state %s',
                        caller.name, self.short_press_time, self.long_press_time,
                        highlow_to_str(self.state_when_pressed))

    def check_button_press(self, caller):
        """checks the duration the contact was closed and
         rises the event configured with that duration

         Parameter:
             - caller : the object of the caller
                        so self.log and self.publish_button_state can be accessed
         """
        #get time during button was closed
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
                    caller.log.info("%s long button press occured on Pin %s (%s)"
                                  " was pressed for %s seconds",
                                  caller.name, caller.pin, caller.gpio_mode, time_delta_seconds)
                    caller.publish_button_state(is_short_press = False)
                else:
                    caller.log.info("%s short button press occured on Pin %s (%s)"
                                  " was pressed for %s seconds",
                                  caller.name, caller.pin, caller.gpio_mode, time_delta_seconds)
                    caller.publish_button_state(is_short_press = True)

class RpiGpioActuator(Actuator):
    """Allows for setting a GPIO pin to high or low on command. Also supports
    toggling.
    """

    def __init__(self, connections, dev_cfg):
        """Initializes the GPIO subsystem and sets the pin to the InitialState.
        If InitialState is not povided in paams it defaults to GPIO.HIGH. If
        "SimulateButton" is defined on any message will result in the pin being set to
        HIGH for half a second and then back to LOW.

        Parameters:
            - "Pin": The GPIO pin in BCM numbering
            - "InitialState": The pin state to set when coming online, defaults
            to "OFF".
            - "SimulateButton": Optional parameter that when set to "True" causes any
            message received to result in setting the pin to HIGH, sleep for
            half a second, then back to LOW.
        """
        super().__init__(connections, dev_cfg)

        self.gpio_mode = set_gpio_mode(dev_cfg, self.log)

        self.pin = int(dev_cfg["Pin"])
        self.invert = dev_cfg.get("InvertOut", False)

        try:
            self.init_state = GPIO.HIGH if dev_cfg["InitialState"] else GPIO.LOW
        except KeyError:
            self.init_state = GPIO.LOW

        try:
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, self.init_state)
        except ValueError as err:
            self.log.error("%s could not setup GPIO Pin %d (%s). "
                           "Make sure the pin number is correct. Error Message: %s",
                           self.name, self.pin, self.gpio_mode, err)

        try:
            self.sim_button = dev_cfg["SimulateButton"]
        except KeyError:
            self.sim_button = dev_cfg.get("Toggle", False)

        #default debaunce time 0.15 seconds
        self.toggle_debounce = float(dev_cfg.get("ToggleDebounce", 0.15))
        self.last_toggle = datetime.datetime.fromordinal(1)

        #remember the current output state
        if self.sim_button:
            self.current_state = None
        else:
            if self.invert:
                self.current_state = not self.init_state
            else:
                self.current_state = self.init_state

        #verify that defined Triggers in Connections section are valid
        verify_connections_layout(self.comm, self.log, self.name, [])

        self.log.info("Configued RpiGpioActuator %s: pin %d (%s) on with SimulateButton %s",
                      self.name, self.pin, self.gpio_mode, self.sim_button)
        self.log.debug("%s has following configured connections: \n%s",
                       self.name, yaml.dump(self.comm))

        # publish inital state to cmd_src
        self.publish_actuator_state()

    def on_message(self, msg):
        """Called when the actuator receives a message. If SimulateButton is not enabled
        sets the pin to HIGH if the message is ON and LOW if the message is OFF.
        """
        # ignore command echo which occure with multiple connections:
        # do nothing when the command (msg) equals the current state,
        # ignor this on SimulateButton mode
        if not self.sim_button:
            if msg in ("ON", "OFF"):
                if self.current_state == strtobool(msg):
                    self.log.info("%s revieved command %s"
                                  " which is equal to current output state. Ignoring command!",
                                  self.name, msg)
                    return
            elif is_toggle_cmd(msg):
                # If the string has length 26 and the char at index 10
                # is T then its porbably a ISO 8601 formated datetime value,
                # which was send from RpiGpioSensor
                time_now = datetime.datetime.now()
                seconds_since_toggle = (time_now - self.last_toggle).total_seconds()
                if seconds_since_toggle < self.toggle_debounce:
                    # filter close toggle commands to make sure no double switching occures
                    self.log.info("%s received toggle command %s"
                                  " within debounce time. Ignoring command!",
                                  self.name, msg)
                    return

                self.last_toggle = time_now
                msg = "TOGGLE"

        self.log.info("%s received command %s, SimulateButton = %s, Invert = %s, Pin = %d (%s)",
                      self.name, msg, self.sim_button, self.invert, self.pin, self.gpio_mode)

        # SimulateButton on then off.
        if self.sim_button:
            self.log.info("%s toggles pin %s (%s) %s to %s",
                          self.name, self.pin, self.gpio_mode,
                          highlow_to_str(self.init_state),
                          highlow_to_str(not self.init_state))
            GPIO.output(self.pin, int(not self.init_state))
            #  "sleep" will block a local connecten and therefore
            # distort the time detection of button press event's
            sleep(.5)
            self.log.info("%s toggles pin %s (%s) %s to %s",
                          self.name, self.pin, self.gpio_mode,
                          highlow_to_str(not self.init_state),
                          highlow_to_str(self.init_state))
            GPIO.output(self.pin, self.init_state)

        # Turn ON/OFF based on the message.
        else:
            out = None
            if msg == "ON":
                out = GPIO.HIGH
            elif msg == "OFF":
                out = GPIO.LOW
            elif msg == "TOGGLE":
                out = int(not self.current_state)

            if out is None:
                self.log.error("%s bad command %s", self.name, msg)
            else:
                self.current_state = out
                if self.invert:
                    out = int(not out)

                self.log.info("%s set pin %d (%s) to %s",
                              self.name, self.pin, self.gpio_mode,
                              highlow_to_str(out))
                GPIO.output(self.pin, out)

                #publish own state back to remote connections
                self.publish_actuator_state()

    def publish_actuator_state(self):
        """Publishes the current state of the actuator."""
        msg = "ON" if self.current_state else "OFF"
        self._publish(msg, self.comm)

    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up GPIO outputs, invoked via Pin %d (%s)",
                       self.pin, self.gpio_mode)
        # make sure cleanup runs only once
        if GPIO.getmode() is not None:
            GPIO.cleanup()
