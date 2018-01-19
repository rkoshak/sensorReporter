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

 Script: rokuAddr.py
 Author: Rich Koshak
 Date:   September 14, 2016
 Purpose: Polls the network and reports the addresses of ROKUs

"""

import sys
import socket
import re
import ConfigParser

class rokuAddr:
    """Represents a sensor which polls for Roku's on the network's current IP addresses"""

    def __init__(self, publisher, logger, params, sensors, actuators):
        """Creates the ssdp request and sets parameters"""

        self.logger = logger
        self.logger.info('----------Configuring rokuAddr')

        self.ssdpRequest = "M-SEARCH * HTTP/1.1\r\n" + \
                           "HOST: 239.255.255.250:1900\r\n" + \
                           "Man: \"ssdp:discover\"\r\n" + \
                           "MX: 5\r\n" + \
                           "ST: roku:ecp\r\n\r\n"
        socket.setdefaulttimeout(10)

        self.rokus = {}
        self.ips = {}
        i = 1
        name = 'Name%s' % (i)
        destination = 'Destination%s' % (i)
        done = False
        while not done:
            try:
                self.rokus[params(name)] = params(destination)
                self.logger.info("Publishing the IP address for %s to %s" % (params(name), params(destination)))
                i += 1
                name = 'Name%s' % (i)
                destination = 'Destination%s' % (i)
            except ConfigParser.NoOptionError:
                done = True

        self.publish = publisher
        self.poll = int(params("Poll"))
        self.checkState()

    def checkState(self):
        """Detects and publishes any state change"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(self.ssdpRequest, ("239.255.255.250", 1900))
        while True:
            try:
                resp = sock.recv(1024)
                matchObj = re.match(r'.*USN: uuid:roku:ecp:([\w\d]{12}).*LOCATION: (http://.*/).*', resp, re.S)
                name = matchObj.group(1)
                ip = matchObj.group(2)
                if name not in sorted(self.ips.keys()) or self.ips[name] != ip:
                  self.logger.info('%s is now at %s' % (name, ip))
                  self.ips[name] = ip
                  self.publish(self.ips[name], self.rokus[name])
                else :
                  self.logger.info('%s is still at %s' % (name, ip))
            except socket.timeout:
                break
        sock.close()
        
    def publishStateImpl(self, data, destination):
        for conn in self.publish:
            conn.publish(data, destination)

    def publishState(self):
        """Publishes the current state"""
        for name in self.ips:
            self.publishStateImpl(self.ips[name], self.rokus[name])

    def cleanup(self):
        """Does nothing"""
