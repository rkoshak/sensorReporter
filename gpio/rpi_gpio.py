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
import RPi.GPIO as GPIO
from core.sensor import Sensor
from core.actuator import Actuator
from core.utils import parse_values
from distutils.util import strtobool 

# Set to use BCM numbering.
GPIO.setmode(GPIO.BCM)

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
            - "Pin": the GPIO pin in BCM numbering
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

        self.pin = int(params("Pin"))

        # Allow users to override the 0/1 pin values.
        self.values = parse_values(params, ["CLOSED", "OPEN"])

        self.log.debug("Configured %s for CLOSED and %s for OPEN", self.values[0], self.values[1])

        pud = GPIO.PUD_UP if params("PUD") == "UP" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

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
        self.destination = params("Destination")

        if self.poll < 0 and event_detection == "NONE":
            raise ValueError("Event detection is NONE but polling is OFF")
        if self.poll > 0 and event_detection != "NONE":
            raise ValueError("Event detection is {} but polling is {}"
                             .format(event_detection, self.poll))

        self.log.info("Configured RpiGpioSensor: pin %d on destination %s with PUD %s"
                      " and event detection %s", self.pin, self.destination, pud,
                      event_detection)

        # We've a first reading so publish it.
        self.publish_state()

    def check_state(self):
        """Checks the current state of the pin and if it's different from the
        last state publishes it. With event detection this method gets called
        when the GPIO pin changed states. When polling this method gets called
        on each poll.
        """
        value = GPIO.input(self.pin)
        if value != self.state:
            self.log.info("Pin %s changed from %s to %s", self.pin, self.state, value)
            self.state = value
            self.publish_state()

    def publish_state(self):
        """Publishes the current state of the pin."""
        msg = self.values[0] if self.state == GPIO.LOW else self.values[1]
        self._send(msg, self.destination)

    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        GPIO.cleanup()

class RpiGpioActuator(Actuator):
    """Allows for setting a GPIO pin to high or low on command. Also supports
    toggling.
    """

    def __init__(self, connections, params):
        """Initializes the GPIO subsystem and sets the pin to the InitialState.
        If InitialState is not povided in paams it defaults to GPIO.HIGH. If
        "Toggle" is defined on any message will result in the pin being set to
        HIGH for half a second and then back to LOW.

        Parameters:
            - "Pin": The GPIO pin in BCM numbering
            - "InitialState": The pin state to set when coming online, defaults
            to "OFF".
            - "Toggle": Optional parameter that when set to "True" causes any
            message received to result in setting the pin to HIGH, sleep for
            half a second, then back to LOW.
        """
        super().__init__(connections, params)
        self.pin = int(params("Pin"))
        GPIO.setup(self.pin, GPIO.OUT)

        out = GPIO.LOW
        try:
            self.init_state = GPIO.HIGH if params("InitialState") == "ON" else GPIO.LOW
            # out = GPIO.HIGH if params("InitialState") == "ON" else GPIO.LOW
        except NoOptionError:
            pass
        GPIO.output(self.pin, self.init_state)
        
        try:
            self.toggle = strtobool(params("Toggle"))
        except NoOptionError:
            self.toggle = False

        self.log.info("Configued RpoGpuiActuator: pin %d on destination %s with "
                      "toggle %s", self.pin, self.cmd_src, self.toggle)

    def on_message(self, msg):
        """Called when the actuator receives a message. If Toggle is not enabled
        sets the pin to HIGH if the message is ON and LOW if the message is OFF.
        """
        self.log.info("Received command on %s: %s Toggle = %s Pin = %d",
                      self.cmd_src, msg, self.toggle, self.pin)

        # Toggle on then off.
        if self.toggle:
            self.log.info("Toggling pin %s %s to %s", self.pin, self.highlow_to_str(self.init_state), self.highlow_to_str(not self.init_state))
            GPIO.output(self.pin, int(not self.init_state))
            sleep(.5)
            self.log.info("Toggling pin %s %s to %s", self.pin, self.highlow_to_str(not self.init_state), self.highlow_to_str(self.init_state))
            GPIO.output(self.pin, self.init_state)

        # Turn ON/OFF based on the message.
        else:
            out = None
            if msg == "ON":
                out = GPIO.HIGH
            elif msg == "OFF":
                out = GPIO.LOW

            if out == None:
                self.log.error("Bad command %s", msg)
            else:
                self.log.info("Setting pin %d to %s", self.pin,
                              "HIGH" if out == GPIO.HIGH else "LOW")
                GPIO.output(self.pin, out)
    
    @staticmethod            
    def highlow_to_str(output):
        if output:
            return "HIGH"
        else:
            return "LOW"
