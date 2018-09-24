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

 Script: rpiGPIOConn.py
 Author: markrad
 Date:   December 18, 2017
 Purpose: Provides and maintains a connection to a GPIO pin on a Raspberry Pi
"""

import ConfigParser

class rpiGPIOConn:

    def __init__(self, msgProc, logger, params, sensors, actuators):
        """Sets up the GPIO pin"""

        self.logger = logger

        self.logger.info("Configuring GPIO connection for actuators %s" % (params("actuator")))

        self.actuatorName = params("Actuator")
        self.actuators = actuators
        self.values = []
        
        try:
            self.values = params("Values").split(",")
        except ConfigParser.NoOptionError:
            self.values = ["OFF", "ON"]
        
        if len(self.values) != 2:
            self.logger.error("Invalid Values option passed for " + self.actuatorName)
        else:
            self.logger.info("Sending OFF for %s and ON for %s" % (self.values[0], self.values[1]))

    def publish(self, message, unused):
        """Called by others to publish a message - must be value from Values option"""
    
        try:
            if (message.upper() == self.values[0].upper()):
                self.logger.debug("Publishing OFF to " + self.actuatorName)
                self.actuators[self.actuatorName].actOn("OFF")
            elif (message.upper() == self.values[1].upper()):
                self.logger.debug("Publishing ON to " + self.actuatorName)
                self.actuators[self.actuatorName].actOn("ON")
            else:
                self.logger.debug(self.values[0].upper())
                self.logger.debug(self.values[1].upper())
                self.logger.error('Unknwon value passed to rpiGPIOConn (%s) : %s' % (self.actuatorName, message))
        except KeyError:
            # Actuator may not yet be set up
            pass

    def register(self, subTopic, msgHandler):
        """ NoOp """
