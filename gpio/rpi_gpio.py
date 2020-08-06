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
"""
import logging
from configparser import NoOptionError
import RPi.GPIO as GPIO
from core.sensors import sensors

log = logging.getLogger(__name__.split(".")[1])

# TODO Callbacks and Actuators
class RpiGpioSensor(Sensor):
    """Publishes the current state of a configured GPIO pin."""

    def __init__(self, publishers, params):
        super().__init__(publishers, params, log)

        # Set to use BCM numbering.
        GPIO.setmode(GPIO.BCM)
        self.pin = int(params("Pin"))

        # Allow users to override the 0/1 pin values.
        try:
            split = params("Values").split(",")
            if len(split) != 2:
                log.error("Invalid options for Values: %s, there should only be "
                          "two values separated by a comma. Defaulting to "
                          "CLOSED,OPEN")
                self.values = ["CLOSED", "OPEN"]
            else:
                self.values = [split]
        except NoOptionError:
            self.values = ["CLOSED", "OPEN"]

        log.debug("Configured %s for CLOSED and %s for OPEN", self.values[0], self.values[1])

        pud = GPIO.PUD_UP if params("PUD") == "UP" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

        # Set up event detection.
        try:
            event_detection = params("EventDetection")
            event_map = {"RISING": GPIO.RISING, "FALLING": GPIO.FALLING, "BOTH": GPIO.BOTH}
            if event_detection not in event_map:
                log.error("Invalid event detection specified: %s, one of RISING,"
                          " FALLING, BOTH or NONE are the only allowed values. "
                          "Defaulting to NONE",
                          event_detection)
                event_detection = "NONE"
        except NoOptionError:
            log.info("No event detection specified, falling back to polling")
            event_detection = "NONE"

        if event_detection != "NONE":
            GPIO.add_event_detect(self.pin, event_map[event_detection],
                                  callback=lambda channel: self.check_state)

        self.state = GPIO.input(self.pin)
        self.destination = params("Destination")

        if self.poll < 0 and event_detection == "NONE":
            raise ValueError("Event detection is NONE but polling is OFF")
        elif self.poll > 0 and event_detection != "NONE":
            raise ValueError("Event detection is {} but polling is {}"
                             .format(event_detection, self.poll))

        log.info("Configured RpiGpioSensor: pin %d on destination %s with PUD %s"
                 " and event detection %s", self.pin, self.destination, pud,
                 event_detection)

        # We've a first reading so publish it.
        self.publish_state()

    def check_state(self):
        value = GPIO.input(self.pin)
        if(value != self.state):
            self.state = value
            self.publish_state()

    def publish_state(self):
        msg = self.values[0] if self.state == GPIO.LOW else self.values[1]
        self._send(msg, self.destination)

    def cleanup(self):
        GPIO.cleanup()
