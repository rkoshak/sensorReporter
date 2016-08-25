"""
   Copyright 2016 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: rpiGPIOSensor.py
 Author: Rich Koshak
 Date:   April 19, 2016
 Purpose: Checks the state of the GPIO pin and publishes any changes

 TODO: Take advantage of GPIO.add_event_detect(pin, GPIO.RISING, callback=myFunction) 
       to register for events instead of polling. Use Dash sensor as an example.
"""

import sys
import RPi.GPIO as GPIO

class rpiGPIOSensor:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, publisher, logger, params):
        """Sets the sensor pin to pud and publishes its current value"""

        self.logger = logger
        GPIO.setmode(GPIO.BCM) # uses BCM numbering, not Board numbering
        p = GPIO.PUD_UP if params("PUD")=="UP" else GPIO.PUD_DOWN
        GPIO.setup(int(params("Pin")), GPIO.IN, pull_up_down=p)

        self.pin = int(params("Pin"))
        self.state = GPIO.input(self.pin)
        self.destination = params("Destination")
        self.publish = publisher.publish
        self.poll = float(params("poll"))

        self.logger.info('----------Configuring rpiGPIOSensor: pin {0} on destination {1} with PULL {2}'.format(self.pin, self.destination, params("PUD")))
        self.publishState()

    def checkState(self):
        """Detects and publishes any state change"""
        value = GPIO.input(self.pin)
        if(value != self.state):
            self.state = value
            self.publishState()

    def publishState(self):
        """Publishes the current state"""
        self.publish('CLOSED' if self.state == GPIO.LOW else 'OPEN', self.destination)

    def cleanup(self):
        """Resets the GPIO pins to their default state"""
        GPIO.cleanup()
