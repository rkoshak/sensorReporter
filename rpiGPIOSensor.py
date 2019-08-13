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
"""

import sys
import RPi.GPIO as GPIO
import ConfigParser

class rpiGPIOSensor:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, connections, logger, params, sensors, actuators):
        """Sets the sensor pin to pud and publishes its current value"""

        self.logger = logger
        self.stateCallback = None
        self.params = params
        self.actuators = actuators
        GPIO.setmode(GPIO.BCM) # uses BCM numbering, not Board numbering
        self.pin = int(params("Pin"))
        self.values = []
                
        try:
            if len(params("Values").split(",")) != 2:
                self.logger.error("Invalid Values option passed for " + self.pin)
            else:
                self.values = params("Values").split(",")
        except ConfigParser.NoOptionError:
            self.values = ["CLOSED", "OPEN"]
        
        self.logger.debug("Sending %s for CLOSED and %s for OPEN" % (self.values[0], self.values[1]))
        
        p = GPIO.PUD_UP if params("PUD")=="UP" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=p)

        def eventDetected(channel):
            self.checkState()
        
        try:
            eventDetection = params("EventDetection")

            if (eventDetection=="RISING" or eventDetection=="FALLING" or eventDetection=="BOTH"):

                try:
                    self.logger.debug("Looking for callback")
                    callback = params('StateCallback')
                    self.logger.debug("Attempting to load " + callback)
                    self.stateCallback = __import__(callback, fromlist=[])
                    getattr(self.stateCallback, 'stateChange')
                    init = getattr(self.stateCallback, 'init')
                    init(self.params)
                    self.logger.debug("Found callback")
                except AttributeError:
                    self.logger.error("Imported module does not implement init or stateChange")
                    self.stateCallback = None
                except ConfigParser.NoOptionError:
                    self.logger.debug("No callback specified")
                    self.stateCallback = None
                except Exception as e:
                    self.logger.error("Import failed: " + str(e))
                    self.stateCallback = None
                
                whichEvent = { "RISING": GPIO.RISING, "FALLING": GPIO.FALLING, "BOTH" : GPIO.BOTH }
                
                event = whichEvent[eventDetection]
                GPIO.add_event_detect(int(params("Pin")), event, callback=eventDetected)
            else:
                eventDetection = "NONE"
                self.stateCallback = None
        except ConfigParser.NoOptionError:
            self.logger.debug("No event detection specified")
            self.stateCallback = None

        self.state = GPIO.input(self.pin)
        self.destination = params("Destination")
        self.publish = connections
        self.poll = float(params("Poll"))

        self.logger.info('----------Configuring rpiGPIOSensor: pin {0} on destination {1} with PULL {2} and event detection {3}'.format(self.pin, self.destination, params("PUD"), eventDetection))
        self.publishState()

    def checkState(self):
        """Detects and publishes any state change"""
        value = GPIO.input(self.pin)
        if(value != self.state):
            self.state = value
            
            if (not self.stateCallback is None):
                self.logger.debug('Callback found')
                self.stateCallback.stateChange(self.state, self.params, self.actuators)
            else:
                self.logger.debug('Callback not found')

            self.publishState()

    def publishState(self):
        """Publishes the current state"""
        for conn in self.publish:
            conn.publish(self.values[0] if self.state == GPIO.LOW else self.values[1], self.destination)

    def cleanup(self):
        """Resets the GPIO pins to their default state"""
        GPIO.cleanup()
