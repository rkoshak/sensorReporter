"""
   Copyright 2016 Richard Koshak / Lenny Shirley

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script:      arpScanner.py
 Author:      Rich Koshak / Mark Radbourne
 Date:        September 24, 2018
 Purpose:     Grabs the current ARP cache and reports if a specific MAC address is present.
"""

import sys
import os

if os.name == 'posix' and sys.version_info[0] < 3:
    try:
        import subprocess32 as subprocess
    except ImportError:
        import subprocess
else:
    import subprocess

class arpScanner:
    """Represents a Mac address to search for in arp output"""

    def __init__(self, publisher, logger, params, sensors, actuators):

        self.logger = logger
        self.publish = publisher
        self.address = params("Address").lower()
		
		# Colons in MAC address mess up OpenHab MQTT item syntax so convert to dots
        self.destination = params("Destination") + '/' + self.address.replace(':', '.');
        self.poll = float(params("Poll"))
        self.state = -1;

        self.logger.info("----------Configuring arpSensor: Address = " + self.address + " Destination = " + self.destination)

        self.checkState()

    def checkState(self):
        """Detects and publishes any state change"""
        found = False
        state = 0
        arpList = subprocess.check_output(['arp', '-n']).split('\n')
        
        # Remove blank line
        arpList.pop()
        
        # Remove title
        del arpList[0]
        
        for entry in arpList:
            if entry.split()[2].lower() == self.address:
                found = True
                break

        if found == True:
            state = 1
        else:
            state = 0
            
        if state != self.state:
            self.state = state
            self.publishState()

    def publishState(self):
        """Publishes the current state"""
        stateStr = ""
        
        if self.state == 1:
            stateStr = 'ON'
        else:
            stateStr = 'OFF'
            
        for conn in self.publish:
            conn.publish(stateStr, self.destination)
