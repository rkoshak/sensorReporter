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

        self.address = params("Address")
        self.destination = params("Destination")

        self.log.info("Configuring BTLE sensor: Address = %s Destination = %s",
                      self.address, self.destination)

        self.timeout = int(params("Timeout"))

        if self.poll <= 0:
            raise ValueError("Poll must be greater than 0")
        if self.poll <= self.timeout:
            raise ValueError("Poll must be greater than or equal to Timeout")

        try:
            self.values = params("Values").split(",")
        except NoOptionError:
            self.values = ["ON", "OFF"]
        if len(self.values) != 2:
            raise ValueError("Expected 2 values separated by a comma for Values")

        self.state = None

    def check_state(self):
        """Scans for BTLE packets. If some where found where previously there
        were none the present message is published, and viseversa. Only when
        there is a change in presence is the message published.
        """
        scanner = Scanner().withDelegate(DefaultDelegate())
        devices = scanner.scan(self.timeout)
        found = len([dev for dev in devices if dev.addr == self.address.lower()]) > 0
        if self.state != found:
            self.state = found
            self.publish_state()

    def publish_state(self):
        """Publishes the most recent presence state."""
        self._send(self.values([0] if self.state else self.values[1]),
                   self.destination)
