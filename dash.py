"""
 Script: dash.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Checks the state of the given GPIO pin and publishes any changes
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import traceback
from scapy.all import *

class dash:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, devices, publish, logger, poll):
        """Sets the sensor pin to pull up and publishes its current state"""

        self.logger = logger

        self.logger.info("----------Configuring dash: ")
        for addr in devices:
            self.logger.info("Address: " + addr + " Topic: " + devices[addr])
        self.devices = devices
        self.publish = publish
        self.poll = poll

    def checkState(self):
        """Detects when the Dash button issues an ARP packet and publishes the fact to the topic"""

        try:

            def arp_display(pkt):
                if ARP in pkt:
                    if pkt[ARP].op == 1: #who-has (request)
                        if pkt[ARP].psrc == '0.0.0.0': # ARP Probe
                            if self.devices[pkt[ARP].hwsrc] != None:
                                self.logger.info("Dash button pressed: " + pkt[ARP].hwsrc)
                                self.publish("Pressed", self.devices[pkt[ARP].hwsrc])
                            else:
                                self.logger.info("Received an ARP packet from an unknown mac: " + pkt[ARP].hwsrc)

            self.logger.info("Dash: kicking off ARP sniffing")
            print sniff(prn=arp_display, filter="arp", store=0, count=0)
            # Never returns
            self.logger.info("Dash: you should never see this")
        except:
            self.logger.error("Unexpected error in dash: %s", sys.exc_info()[0])
            traceback.print_exc(file=sys.stdout)    

    def publishState(self):
        """Publishes the current state"""

