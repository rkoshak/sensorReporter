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

 Script  rpiGPIOActuator.py
 Author: Rich Koshak
 Date:   April 19, 2016
 Purpose: Changes the state of the configured pin on command
"""

import sys
import time
import RPi.GPIO as GPIO

class rpiGPIOActuator:
    """Represents an actuator connected to a GPIO pin"""

    def __init__(self, connection, logger, params):
        """Sets the output and changes its state when it receives a command"""

        self.logger = logger

        self.pin = int(params("Pin"))

        GPIO.setmode(GPIO.BCM) # uses BCM numbering, not Board numbering
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.HIGH)

        self.destination = params("Topic")
        self.connection = connection
        self.toggle = bool(params("Toggle"))

        self.logger.info('----------Configuring rpiGPIOActuator: pin {0} on destination {1} with toggle {2}'.format(self.pin, self.destination, self.toggle))
        self.connection.register(self.destination, self.on_message)

    def on_message(self, client, userdata, msg):
        """Process a message"""
        self.logger.info('Received command on {0}: {1} Toggle = {2} PIN = {3}'.format(self.destination, msg.payload, self.toggle, self.pin))
        if self.toggle == "True":
            self.logger.info('Toggling pin %s HIGH to LOW' % (self.pin))
            GPIO.output(self.pin, GPIO.LOW)
            time.sleep(.5)
            GPIO.output(self.pin, GPIO.HIGH)
            self.logger.info('Toggling pin %s LOW to HIGH' % (self.pin))
        else:
            out = GPIO.LOW if msg.payload == "ON" else GPIO.HIGH
            GPIO.output(self.pin, out)

