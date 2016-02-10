"""
 Script:  restConn.py
 Author:  Lenny Shirley <http://www.lennysh.com>
 Date:    February 8, 2016
 Purpose: Provides a connection to the OpenHAB REST API
"""

import sys
import requests
from requests.exceptions import ConnectionError

class restConnection(object):
    """Centralizes the REST logic"""

    def config(self, logger, url):
        """Configures the client"""
        
        self.logger = logger
        self.url = url

    def publish(self, message, item):
        """Called by others to publish a message to an OpenHAB item"""

        try:
            print self.url + item + "/state/" + message
            requests.put(self.url + item + "/state/",data=message)
            self.logger.info("Published message " + message + " to " + item)
        except:
            msg = "Unexpected error publishing message: %s" % (sys.exc_info()[0])
            print msg
            self.logger.error(msg)
