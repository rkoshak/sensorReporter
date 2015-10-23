"""
 Script: gpioSensor.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Checks the state of the given GPIO pin and publishes any changes
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import webiopi

class gpioSensor:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, pin, topic, pud, publish, logger, poll):
        """Sets the sensor pin to pull up and publishes its current state"""

        self.logger = logger

        self.logger.info("----------Configuring gpioSensor: pin " + str(pin) + " on topic " + topic + " with PULL " + pud)
        self.gpio = webiopi.GPIO
        self.pin = pin
        pud = self.gpio.PUD_UP if pud=="UP" else self.gpio.PUD_DOWN
        self.gpio.setup(pin, self.gpio.IN, pull_up_down=pud)
        self.state = self.gpio.digitalRead(pin)
        self.topic = topic
        self.publish = publish
        self.poll = poll

        self.publishState()

    def checkState(self):
        """Detects and publishes any state change"""

        value = self.gpio.digitalRead(self.pin)
        if(value != self.state):
            self.state = value
            self.publishState()

    def publishState(self):
        """Publishes the current state"""

        self.publish("CLOSED" if self.state == self.gpio.LOW else "OPEN", self.topic)
