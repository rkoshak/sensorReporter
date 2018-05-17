"""
   Copyright 2016 Lenny Shirley

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script:  restConn.py
 Author:  Lenny Shirley <http://www.lennysh.com>
 Date:    February 8, 2016
 Purpose: Provides a connection to the OpenHAB REST API
"""

import sys
import requests
from requests.exceptions import ConnectionError

debug = 1

class restConnection(object):
    """Centralizes the REST logic"""

    def __init__(self, msgProc, logger, params, sensors, actuators):
        """Configures the client"""
        
        # ignore msgProc
        self.logger = logger
        self.url = params("URL")
        
#    def register(unused1, unused2):
        # Do nothing

    def publish(self, message, destination):
        """Called by others to publish a message to a Destination"""

        try:
            msg = "Published message '%s' to '%s'" % (message, destination)
            if debug:
                print msg
            requests.put(self.url + destination + "/state/",data=message)
            self.logger.info(msg)
        except:
            msg = "Unexpected error publishing message: %s" % (sys.exc_info()[0])
            print msg
            self.logger.error(msg)
