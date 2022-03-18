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
from configparser import NoOptionError
from distutils.util import strtobool
import datetime
from RPi import GPIO
from core.sensor import Sensor
from core.actuator import Actuator
from core.utils import parse_values, is_toggle_cmd

def set_gpio_mode(params, log):
    """Set GPIO mode (BCM or BOARD) for all Sensors and Actuators
    put a Warning if it was changed or set multible times
    Parameters:
        - params : the lamda function that stores the config values for a sensor
        - log    : the self.log instance of the calling sensor
    """
    try:
        gpio_mode = GPIO.BCM if params("PinNumbering") == "BCM" else GPIO.BOARD
    except NoOptionError:
        gpio_mode = GPIO.BCM

    try:
        GPIO.setmode(gpio_mode)
    except ValueError:
        log.error("GPIO PinNumbering was set differently before"
                    " make sure is is only set in the [DEFAULT] section.")
        return "Err: not set"
    return "BCM" if gpio_mode == GPIO.BCM else "BOARD"

class RpiGpioSensor(Sensor):
    """Publishes the current state of a configured GPIO pin."""

    def __init__(self, publishers, params):
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
        super().__init__(publishers, params)

        self.gpio_mode = set_gpio_mode(params, self.log)

        self.pin = int(params("Pin"))
        self.destination = params("Destination")

        # Allow users to override the 0/1 pin values.
        self.values = parse_values(params, ["CLOSED", "OPEN"])

        self.log.debug("Configured %s for CLOSED and %s for OPEN", self.values[0], self.values[1])

        pud = GPIO.PUD_UP if params("PUD") == "UP" else GPIO.PUD_DOWN
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)
        except ValueError as err:
            self.log.error("Could not setup GPIO Pin %d (%s), destination %s. "
                           "Make sure the pin number is correct. Error Message: %s",
                           self.pin, self.gpio_mode, self.destination, err)

        # Set up event detection.
        try:
            event_detection = params("EventDetection")
            event_map = {"RISING": GPIO.RISING, "FALLING": GPIO.FALLING, "BOTH": GPIO.BOTH}
            if event_detection not in event_map:
                self.log.error("Invalid event detection specified: %s, one of RISING,"
                               " FALLING, BOTH or NONE are the only allowed values. "
                               "Defaulting to NONE",
                               event_detection)
                event_detection = "NONE"
        except NoOptionError:
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

        self.btn = ButtonPressCfg(params, self.log, pud)

        self.log.info("Configued RpiGpioSensor: pin %d (%s) on destination %s with PUD %s",
                      self.pin, self.gpio_mode, self.destination,
                      "UP" if pud == GPIO.PUD_UP else "DOWN")

        self.publish_state()

    def check_state(self):
        """Checks the current state of the pin and if it's different from the
        last state publishes it. With event detection this method gets called
        when the GPIO pin changed states. When polling this method gets called
        on each poll.
        """
        value = GPIO.input(self.pin)
        if value != self.state:
            self.log.info("Pin %s (%s) changed from %s to %s (= %s)",
                          self.pin, self.gpio_mode, self.state, value, self.values[value])
            self.state = value
            self.publish_state()
            self.btn.check_button_press(self)

    def publish_state(self):
        """Publishes the current state of the pin."""
        msg = self.values[0] if self.state == GPIO.LOW else self.values[1]
        self._send(msg, self.destination)

    def publish_button_state(self, is_short_press):
        """send update to destination depending on button press duration"""
        current_time_str = str(datetime.datetime.now())
        #convert datetime to fromat: add T bewteen date and time
        curr_time_java = current_time_str[:10] + "T" + current_time_str[11:]
        if is_short_press:
            self._send(curr_time_java, self.btn.dest_short_press)
        else:
            self._send(curr_time_java, self.btn.dest_long_press)

    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up GPIO inputs, invoked via Pin %d (%s)",
                       self.pin, self.gpio_mode)
        GPIO.remove_event_detect(self.pin)
        # make sure cleanup runs only once
        if GPIO.getmode() is not None:
            GPIO.cleanup()

class ButtonPressCfg():
    """ stores all button related parameters
    """
    def __init__(self, params, log, pud):
        """ read optional button press  related parametes from the config

            Parameters:
            - params : the lamda function that stores the config values for a sensor
            - log    : the self.log instance of the calling sensor
            - pud    : the configured value for the pull up /
                       down resistor either GPIO.PUD_UP or GPIO.PUD_DOWN
        """
        try:
            self.dest_short_press = params("Short_Press-Dest")
            self.high_time = None
            try:
                #expect threshold in seconds
                self.short_press_time = float(params("Short_Press-Threshold"))
            except NoOptionError:
                self.short_press_time = 0

            try:
                self.dest_long_press = params("Long_Press-Dest")
                try:
                    self.long_press_time = float(params("Long_Press-Threshold"))
                except NoOptionError:
                    self.long_press_time = 0
                    log.error("No 'Long_Press-Threshold' "
                                   "configured for Long_Press-Dest: %s",
                                    self.dest_long_press)
            except NoOptionError:
                self.long_press_time = 0
        except NoOptionError:
            self.dest_short_press = None

        try:
            self.state_when_pressed = GPIO.LOW if params("Btn_Pressed_State")=="LOW" else GPIO.HIGH
        except NoOptionError:
            #remember expacted state for contact closed
            self.state_when_pressed = GPIO.LOW if pud == GPIO.PUD_UP else GPIO.HIGH

    def check_button_press(self, caller):
        """checks the duration the contact was closed and
         rises the event configured with that duration

         Parameter:
             - caller : the object of the caller
                        so self.log and self.publish_button_state can be accessed
         """
        #if dest_short_press is not configured exit
        if self.dest_short_press is None:
            return

        #get time during button was closed
        if caller.state == self.state_when_pressed:
            self.high_time = datetime.datetime.now()
        elif self.high_time is None:
            caller.log.warning("Expected contact closed before release."
                               " 'Btn_Pressed_State' is probably configured wrong"
                               " for Pin: %s, Destination: %s", caller.pin, caller.destination)
        else:
            time_delta_seconds = (datetime.datetime.now() - self.high_time).total_seconds()
            if time_delta_seconds > self.short_press_time:
                if self.long_press_time != 0 and time_delta_seconds > self.long_press_time:
                    caller.log.info("Long button press occured on Pin %s (%s)"
                                  " was pressed for %s seconds",
                                  caller.pin, self.dest_long_press, time_delta_seconds)
                    caller.publish_button_state(is_short_press = False)
                else:
                    caller.log.info("Short button press occured on Pin %s (%s)"
                                  " was pressed for %s seconds",
                                  caller.pin, self.dest_short_press, time_delta_seconds)
                    caller.publish_button_state(is_short_press = True)

class RpiGpioActuator(Actuator):
    """Allows for setting a GPIO pin to high or low on command. Also supports
    toggling.
    """

    def __init__(self, connections, params):
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
        super().__init__(connections, params)

        self.gpio_mode = set_gpio_mode(params, self.log)

        self.pin = int(params("Pin"))

        try:
            self.invert = bool(strtobool(params("InvertOut")))
        except NoOptionError:
            self.invert = False

        try:
            self.toggle_cmd_src = params("ToggleCommandSrc")
            super()._register(self.toggle_cmd_src, self.on_message)
        except NoOptionError:
            pass

        try:
            self.init_state = GPIO.HIGH if params("InitialState") == "ON" else GPIO.LOW
        except NoOptionError:
            self.init_state = GPIO.LOW

        try:
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, self.init_state)
        except ValueError as err:
            self.log.error("Could not setup GPIO Pin %d (%s), CommandSrc %s. "
                           "Make sure the pin number is correct. Error Message: %s",
                           self.pin, self.gpio_mode, self.cmd_src, err)

        try:
            self.sim_button = bool(strtobool(params("SimulateButton")))
        except NoOptionError:
            try:
                self.sim_button = bool(strtobool(params("Toggle")))
            except NoOptionError:
                self.sim_button = False

        try:
            self.toggle_debounce = float(params("ToggleDebounce"))
        except NoOptionError:
            #default debaunce time 0.15 seconds
            self.toggle_debounce = 0.15
        self.last_toggle = datetime.datetime.fromordinal(1)

        #remember the current output state
        if self.sim_button:
            self.current_state = None
        else:
            if self.invert:
                self.current_state = not self.init_state
            else:
                self.current_state = self.init_state

        self.log.info("Configued RpiGpioActuator: pin %d (%s) on destination %s with "
                      "SimulateButton %s", self.pin, self.gpio_mode, self.cmd_src, self.sim_button)

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
                    self.log.info("Revieved command for %s = %s"
                                  " which is equal to current output state. Ignoring command!",
                                  self.cmd_src, msg)
                    return
            elif is_toggle_cmd(msg):
                # If the string has length 26 and the char at index 10
                # is T then its porbably a ISO 8601 formated datetime value,
                # which was send from RpiGpioSensor
                time_now = datetime.datetime.now()
                seconds_since_toggle = (time_now - self.last_toggle).total_seconds()
                if seconds_since_toggle < self.toggle_debounce:
                    # filter close toggle commands to make sure no double switching occures
                    self.log.info("Received toggle command for %s = %s"
                                  " within debounce time. Ignoring command!",
                                  self.toggle_cmd_src, msg)
                    return

                self.last_toggle = time_now
                msg = "TOGGLE"

        self.log.info("Received command on %s: %s, SimulateButton = %s, Invert = %s, Pin = %d (%s)",
                      self.cmd_src, msg, self.sim_button, self.invert, self.pin, self.gpio_mode)

        # SimulateButton on then off.
        if self.sim_button:
            self.log.info("Toggling pin %s (%s) %s to %s",
                          self.pin, self.gpio_mode,
                          self.highlow_to_str(self.init_state),
                          self.highlow_to_str(not self.init_state))
            GPIO.output(self.pin, int(not self.init_state))
            #  "sleep" will block a local connecten and therefore
            # distort the time detection of button press event's
            sleep(.5)
            self.log.info("Toggling pin %s (%s) %s to %s",
                          self.pin, self.gpio_mode,
                          self.highlow_to_str(not self.init_state),
                          self.highlow_to_str(self.init_state))
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
                self.log.error("Bad command %s", msg)
            else:
                self.current_state = out
                if self.invert:
                    out = int(not out)

                self.log.info("Setting pin %d (%s) to %s",
                              self.pin, self.gpio_mode,
                              self.highlow_to_str(out))
                GPIO.output(self.pin, out)

                #publish own state back to remote connections
                self.publish_actuator_state()

    def publish_actuator_state(self):
        """Publishes the current state of the actuator."""
        msg = "ON" if self.current_state else "OFF"

        #publish own state, make sure the echo gets filtered
        self._publish(msg, self.cmd_src, filter_echo=True)

    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up GPIO outputs, invoked via Pin %d (%s)",
                       self.pin, self.gpio_mode)
        # make sure cleanup runs only once
        if GPIO.getmode() is not None:
            GPIO.cleanup()

    @staticmethod
    def highlow_to_str(output):
        """Converts (GPIO.)HIGH (=1) and LOW (=0) to the corresponding string

        Parameter: - "output": the GPIO constant (HIGH or LOW)

        Returns string HIGH/LOW
        """
        if output:
            return "HIGH"

        return "LOW"
