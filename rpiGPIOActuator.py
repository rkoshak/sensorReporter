"""
 Script  rpiGPIOActuator.py
 Author: Rich Koshak
 Date:   April 19, 2016
 Purpose: Changes the state of the configured pin on command
"""

import sys
import RPi.GPIO as GPIO

class rpiGPIOActuator:
    """Represents an actuator connected to a GPIO pin"""

    def __init__(self, pin, destination, connection, toggle, logger):
        """Sets the output and changes its state when it receives a command"""

        self.logger = logger
        self.logger.info('----------Configuring rpiGPIOActuator: pin {0} on destination {1} with toggle {2}'.format(pin, destination, toggle))
        
        GPIO.setmode(GPIO.BCM) # uses BCM numbering, not Board numbering
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)

        self.destination = destination
        self.connection = connection
        self.toggle = toggle

        self.connection.register(self.destination, self.on_message)

    def on_message(self, client, userdata, msg):
        """Process a message"""
        self.logger.info('Received command on {0}: {1} Toggle = {2}'.format(self.destination, msg.payload, self.toggle))
        if self.toggle == True:
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(.5)
            GPIO.output(pin, GPIO.LOW)
        else:
            out = GPIO.LOW if msg.payload == "ON" else GPIO.HIGH

