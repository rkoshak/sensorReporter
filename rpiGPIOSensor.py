"""
 Script: rpiGPIOSensor.py
 Author: Rich Koshak
 Date:   April 19, 2016
 Purpose: Checks the state of the GPIO pin and publishes any changes

 TODO: Take advantage of GPIO.add_event_detect(pin, GPIO.RISING, callback=myFunction) 
       to register for events instead of polling. Use Dash sensor as an example.
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import RPi.GPIO as GPIO

class rpiGPIOSensor:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, pin, destination, pud, publish, logger, poll):
        """Sets the sensor pin to pud and publishes its current value"""

        self.logger = logger
        self.logger.info('----------Configuring rpiGPIOSensor: pin {0} on destination {1} with PULL {2}'.format(pin, destination, pud))
        
        GPIO.setmode(GPIO.BCM) # uses BCM numbering, not Board numbering
        p = GPIO.PUD_UP if pud=="UP" else GPIO.PUD_DOWN
        GPIO.setup(pin, GPIO.IN, pull_up_down=p)

        self.pin = pin
        self.state = GPIO.input(self.pin)
        self.destination = destination
        self.publish = publish
        self.poll = poll

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
