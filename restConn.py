"""
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

    def config(self, logger, url):
        """Configures the client"""
        
        self.logger = logger
        self.url = url

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
