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

 Script: dash.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Scans for ARP packets from Amazon Dash buttons
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import traceback
from scapy.all import *
import ConfigParser

class dash:
    """Scans for ARP packets from Dash buttons"""

    def __init__(self, publisher, logger, params, sensors, actuators):
        """Sets the sensor pin to pull up and publishes its current state"""

        self.logger = logger

        self.logger.info("----------Configuring dash: ")
        self.devices = {}
        i = 1
        addr = 'Address%s' % (i)
        destination = 'Destination%s' % (i)
        done = False
        while not done:
          try:
            mac = params(addr)
            self.devices[mac] = params(destination)
            self.logger.info("Sniffing for %s to publish to %s" % (mac, params(destination)))
            i += 1
            addr = 'Address%s' % (i)
            destination = 'Destination%s' % (i)
          except ConfigParser.NoOptionError:
            done = True

        self.publish = publisher
        self.poll = int(params("Poll"))

    def checkState(self):
        """Detects when the Dash button issues an ARP packet and publishes the fact to the topic"""

        try:

            def arp_display(pkt):
              if ARP in pkt and pkt[ARP].op in (1,2): #who-has or is-at
                  if self.devices.get(pkt[ARP].hwsrc, None) != None:
                      self.logger.info("Dash button pressed for: " + self.devices[pkt[ARP].hwsrc])
                      
                      for conn in self.publish:
                        conn.publish("Pressed", self.devices[pkt[ARP].hwsrc])
#                  else:
#                      self.logger.info("Received and ARP packet from an unknown mac: " + pkt[ARP].hwsrc)

            self.logger.info("Dash: kicking off ARP sniffing")
            print sniff(prn=arp_display, filter="arp", store=0, count=0)
            # Never returns
            self.logger.info("Dash: you should never see this")
        except:
            self.logger.error("Unexpected error in dash: %s", sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)    

    def publishState(self):
        """Does nothing"""

