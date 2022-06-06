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
import yaml
from core.sensor import Sensor
from core.utils import configure_device_channel

class ArpSensor(Sensor):
    """Scans the local arp table for the presence of a given MAC address."""

    def __init__(self, publishers, dev_cfg):
        """Expects the following parameters:
        Params:
            - Poll: must be > 0
            - MAC: the mac address to look for
            not
        Raises:
            - KeyError: if any required paramter is not present
            - ValueError: if Poll <= 0
        """
        super().__init__(publishers, dev_cfg)

        self.mac = dev_cfg["MAC"].lower()

        if self.poll <= 0:
            raise ValueError("Poll must be greater than 0")

        self.state = None

        self.log.info("Configuring ARP sensor %s for address %s",
                      self.name, self.mac)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        self.check_state()

        #configure_output for homie etc. after debug output, so self.comm is clean
        configure_device_channel(self.comm, is_output=True,
                                 name=f"{self.mac} present")
        self._register(self.comm)

    def check_state(self):
        """Calls arp and parses the resuts looking for the MAC address. If it's
        presence changes (i.e. absent when last report was present and vise
        versa) that change is published.
        """
        self.log.debug("%s checking arp table.", self.name)
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
            self.log.error("%s command returned an error code: %s\n%s",
                           self.name, ex.returncode, ex.output)
        except subprocess.TimeoutExpired:
            self.log.error("%s arp call took longer than 10 seconds.",
                           self.name)

    def publish_state(self):
        """Publishes ON is the MAC is present, OFF otherwise."""
        send_val = "ON" if self.state else "OFF"
        self.log.debug("%s publishing %s", self.name, send_val)
        self._send(send_val, self.comm)
