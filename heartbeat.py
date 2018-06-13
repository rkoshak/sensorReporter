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

 Script: heartbeat.py
 Author: Rich Koshak
 Date:   October 7, 2016
 Purpose: Sends out a heartbeat message on the polling period
"""

import sys
import time

class heartbeat:
    """Issues a heartbeat message on the polling period"""

    def __init__(self, publisher, logger, params, sensors, actuators):
        """Sets the heartbeat message and destination"""

        self.logger = logger
        self.numDest = params("Num-Dest")
        self.strDest = params("Str-Dest")
        self.publish = publisher
        self.poll = float(params("Poll"))
        self.startTime = time.time()

        self.logger.info('----------Configuring heartbeat to msec destination {0} and str destinatin {1} with interval {2}'.format(self.numDest, self.strDest, self.poll))
        self.publishState()

    def checkState(self):
        """Does nothing"""
        self.publishState()

    def publishState(self):
        """Publishes the heartbeat"""
        uptime = int((time.time() - self.startTime) * 1000)
        for conn in self.publish:
            conn.publish(str(uptime), self.numDest)

        sec = (uptime / (1000)) % 60
        min = (uptime / (1000*60)) % 60
        hr  = (uptime / (1000*60*60)) % 24
        day = uptime / (1000*60*60*24)

        msg = ''
        if day > 0:
          msg += '{0}:'.format(day)
        msg += '{0:02d}:{1:02d}:{2:02d}'.format(hr, min, sec)
        
        for conn in self.publish:
            conn.publish(msg, self.strDest)

    def cleanup(self):
        """Does nothing"""
