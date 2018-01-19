"""
   Copyright 2015 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: gpioSensor.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Checks the state of the given GPIO pin and publishes any changes
 !!DEPRECATED!!
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import webiopi

class gpioSensor:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, publisher, logger, params, sensors, actuators):
        """Sets the sensor pin to pull up and publishes its current state"""

        self.logger = logger

        self.gpio = webiopi.GPIO
        self.pin = int(params.get("Pin"))
        pud = self.gpio.PUD_UP if params.get("PUD")=="UP" else self.gpio.PUD_DOWN
        self.gpio.setup(self.pin, self.gpio.IN, pull_up_down=pud)
        self.state = self.gpio.digitalRead(pin)
        self.destination = params.get("Destination")
        self.publish = publisher.publish
        self.poll = params("Poll")
        self.logger.info("----------Configuring gpioSensor: pin %s on destination %s with PULL %s" % (str(self.pin), self.destination, self.pud))

        self.publishState()

    def checkState(self):
        """Detects and publishes any state change"""

        value = self.gpio.digitalRead(self.pin)
        if(value != self.state):
            self.state = value
            self.publishState()

    def publishState(self):
        """Publishes the current state"""

        self.publish("CLOSED" if self.state == self.gpio.LOW else "OPEN", self.destination)
