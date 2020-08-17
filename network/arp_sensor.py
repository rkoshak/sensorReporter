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
"""Checks the ARP table for devices of a given MAC address.
Classes: ArpSensor
"""
import subprocess
from core.sensor import Sensor

class ArpSensor(Sensor):
    """Scans the local arp table for the presence of a given MAC address."""

    def __init__(self, publishers, params):
        """Expects the following parameters:
        Params:
            - Poll: must be > 0
            - MAC: the mac address to look for
            - Destination: where to publish ON if it's present or OFF if it is
            not
        Raises:
            - NoOptionError: if any required paramter is not present
            - ValueError: if Poll <= 0
        """
        super().__init__(publishers, params)

        self.mac = params("MAC").lower()
        self.destination = params("Destination")

        if self.poll <= 0:
            raise ValueError("Poll must be greater than 0")

        self.state = None

        self.log.info("Configuring ARP sensor for address %s and destiantion %s",
                      self.mac, self.destination)

        self.check_state()

    def check_state(self):
        """Calls arp and parses the resuts looking for the MAC address. If it's
        presence changes (i.e. absent when last report was present and vise
        versa) that change is published.
        """
        self.log.debug("Checking arp table.")
        try:
            cmd_args = ["arp", "-n"]
            results = subprocess.check_output(cmd_args, shell=False,
                                              universal_newlines=True,
                                              timeout=10).rstrip().split('\n')
            found = self.mac in [entry.split()[2].lower() for entry in results]
            if found != self.state:
                self.state = found
                self.publish_state()
        except subprocess.CalledProcessError as ex:
            self.log.error("Command returned an error code: %s\n%s",
                           ex.returncode, ex.output)
        except subprocess.TimeoutExpired:
            self.log.error("arp call took longer than 10 seconds.")

    def publish_state(self):
        """Publishes ON is the MAC is present, OFF otherwise."""
        send_val = "ON" if self.state else "OFF"
        self.log.debug("Publishing %s for %s", send_val, self.destination)
        self._send(send_val, self.destination)
