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
from bluepy.btle import Scanner, DefaultDelegate
from core.sensor import Sensor
from core.utils import parse_values, get_sequential_params

class BtleSensor(Sensor):
    """Uses BluePy to scan for BTLE braodcasts from a device with a given MAC
    address and publishes whehter or not it is present.
    """

    def __init__(self, publishers, params):
        """Initializes the BTLE scanner.
        Parameters:
            - Poll: must be > 0 and > Timeout
            - Address: BTLE MAC address of the device
            - Destination: Where to publish the presence of absence message
            - Timeout: Maximum amount of time to wait for BTLE packets
            - Values: optional, if present should have two values separated by
            a comma, the first value being the present message and the second
            the absence message that will be published to the destination.
            Defaults to "ON" and "OFF".
        """
        super().__init__(publishers, params)

        addresses = get_sequential_params(params, "Address")
        destinations = get_sequential_params(params, "Destination")
        laststates = [None] * len(addresses)
        if len(addresses) != len(destinations):
            raise ValueError("List of addresses and destinations do not match up!")
        self.devices = dict(zip(addresses, destinations))
        self.states = dict(zip(addresses, laststates))

        self.log.info("Configuring BTLE sensor")

        self.timeout = int(params("Timeout"))

        if self.poll <= 0:
            raise ValueError("Poll must be greater than 0")
        if self.poll <= self.timeout:
            raise ValueError("Poll must be greater than or equal to Timeout")

        self.values = parse_values(params, ("ON", "OFF"))

    def check_state(self):
        """Scans for BTLE packets. If some where found where previously there
        were none the present message is published, and viseversa. Only when
        there is a change in presence is the message published.
        """
        self.log.debug("Checking for BTLE devices")
        scanner = Scanner().withDelegate(DefaultDelegate())
        # Scan for packets and get a list of the addresses found
        scanneddevs = [dev.addr for dev in scanner.scan(self.timeout)]
        # Get a list of addresses for which one or more packets were found during
        # the scan.
        self.log.debug("Packets is %s", scanneddevs)
        founddevs = [mac for mac in self.devices if scanneddevs.count(mac) > 0]
        self.log.debug("Found %s", founddevs)

        # Publish ON for those addresses where packets were found and the
        # previous reported state isn't ON.
        for mac in [mac for mac in founddevs if not self.states[mac]]:
            self.log.debug("Publishing %s as ON", mac)
            self.states[mac] = True
            self._send(self.values[0], self.devices[mac])
        # Publish OFF for those addresses where no packets where found and the
        # previous reported state isn't OFF.
        for mac in ([mac for mac in self.devices
                     if mac not in founddevs and self.states[mac]
                     or self.states[mac] is None]):
            self.log.debug("Publishing %s as OFF", mac)
            self.states[mac] = False
            self._send(self.values[1], self.devices[mac])

    def publish_state(self):
        """Publishes the most recent presence state."""
        for mac in self.states:
            self._send(self.values[0] if self.states[mac] else self.values[1],
                       self.devices[mac])
