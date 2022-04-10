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
"""Implements scanning for a BTLE device with a given address.
Classes:
    - BtleSensor
"""
import yaml
from bluepy.btle import Scanner, DefaultDelegate
from core.sensor import Sensor
from core.utils import parse_values, get_dict_of_sequential_param__output, verify_connections_layout

class BtleSensor(Sensor):
    """Uses BluePy to scan for BTLE braodcasts from a device with a given MAC
    address and publishes whehter or not it is present.
    """

    def __init__(self, publishers, dev_cfg):
        """Initializes the BTLE scanner.
        dev_cfg:
            - Poll: must be > 0 and > Timeout
            - AddressX: sequential list of MAC addresses to look for
            - Timeout: Maximum amount of time to wait for BTLE packets
            - Values: optional, if present should have two values separated by
            a comma, the first value being the present message and the second
            the absence message that will be published to the destination.
            Defaults to "ON" and "OFF".

        Raises:
            - KeyError: when a required parameter doesn't exist
            - ValueError: when the list of Addresses and Destinations don't
            match up or Poll is too small.
        """
        super().__init__(publishers, dev_cfg)

        self.devices = get_dict_of_sequential_param__output(dev_cfg, "Address", "Destination")
        verify_connections_layout(self.comm, self.log, self.name, list(self.devices.values()))

        self.states = dict.fromkeys(list(self.devices.keys()), None)

        self.log.info("Configuring BTLE sensor %s", self.name)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        self.timeout = int(dev_cfg["Timeout"])

        if self.poll <= 0:
            raise ValueError("Poll must be greater than 0")
        if self.poll <= self.timeout:
            raise ValueError("Poll must be greater than or equal to Timeout")

        self.values = parse_values(dev_cfg, ("ON", "OFF"))

    def check_state(self):
        """Scans for BTLE packets. If some where found where previously there
        were none the present message is published, and viseversa. Only when
        there is a change in presence is the message published.
        """
        self.log.debug("%s checking for BTLE devices", self.name)
        scanner = Scanner().withDelegate(DefaultDelegate())
        # Scan for packets and get a list of the addresses found
        scanneddevs = [dev.addr for dev in scanner.scan(self.timeout)]
        # Get a list of addresses for which one or more packets were found during
        # the scan.
        self.log.debug("%s packets is %s", self.name, scanneddevs)
        founddevs = [mac for mac in self.devices if scanneddevs.count(mac) > 0]
        self.log.debug("%s found %s", self.name, founddevs)

        # Publish ON for those addresses where packets were found and the
        # previous reported state isn't ON.
        for mac in [mac for mac in founddevs if not self.states[mac]]:
            self.log.debug("%s publishing %s as ON", self.name, mac)
            self.states[mac] = True
            self._send(self.values[0],self.comm, self.devices[mac])
        # Publish OFF for those addresses where no packets where found and the
        # previous reported state isn't OFF.
        for mac in ([mac for mac in self.devices
                     if mac not in founddevs and self.states[mac]
                     or self.states[mac] is None]):
            self.log.debug("%s publishing %s as OFF", self.name, mac)
            self.states[mac] = False
            self._send(self.values[1], self.comm, self.devices[mac])

    def publish_state(self):
        """Publishes the most recent presence state."""
        for (mac, state) in self.states.items():
            self._send(self.values[0] if state else self.values[1],
                       self.comm, self.devices[mac])
