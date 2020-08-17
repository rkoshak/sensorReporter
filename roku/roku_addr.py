# Copyright 2020 Richard Koshak
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Sends an SSDP Requests for the URL for all the Rokus on the same network as
the script is running and publishes the URLs. The destination is the device
name (i.e. serial number).

Classes:
    - RokuAddressSensor: Class that issues an SSDP request and publishes the URLs
    for all the discovered Rokus.
"""
import socket
import re
from core.sensor import Sensor

SSDP_REQUEST = (b"M-SEARCH * HTTP/1.1\r\n"
                b"HOST: 239.255.255.250:1900\r\n"
                b"Man: \"ssdp:discover\"\r\n"
                b"MX: 5\r\n"
                b"ST: roku:ecp\r\n\r\n")

class RokuAddressSensor(Sensor):
    """Sends an SSDP request and publishes the URL for all the discovered Rokus.
       Poll should be more than 19."""

    def __init__(self, publishers, params):
        """Initialize the sensor. This is not a self running sensor so Poll must
        be a positive number."""
        super().__init__(publishers, params)

        self.log.info("Configuing Roku Address Sensor")
        if self.poll <= 0:
            raise ValueError("RokuAddressSensor requires a positive Poll value: "
                             "%s", self.poll)

        socket.setdefaulttimeout(10)

        self.ips = {}

        # Kickoff a poll for the configured Rokus.
        self.check_state()

    def check_state(self):
        """Issues the request and waits for 19 seconds for responses from Rokus.
        The current states are published on every poll.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(SSDP_REQUEST, ("239.255.255.250", 1900))
        while True:
            try:
                resp = str(sock.recv(1024))
                match = re.match(r'.*USN: uuid:roku:ecp:([\w\d]{12}).*LOCATION: (http://.*/).*',
                                 resp, re.S)
                name = match.group(1)
                ip = match.group(2)
                if name not in sorted(self.ips.keys()) or self.ips[name] != ip:
                    self.log.info("%s is now at %s", name, ip)
                    self.ips[name] = ip
                else:
                    self.log.debug("%s is still at %s", name, ip)
            except socket.timeout:
                break
        sock.close()
        self.publish_state()

    def publish_state(self):
        """Publishes the URL using the Roku device name as the destination."""
        for name in self.ips:
            self._send(self.ips[name], name)
