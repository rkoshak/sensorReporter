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
"""Contains sensors that look to see if given BT devices are present. Does not
look for BTLE devices.

Classes:
    -SimpleBtSensor: Looks for a device by address and if it finds it publishes
    ON.
    - BtRssiSensor: Looks for a device by address and it it sees it enough times
    publishes ON.
"""
from typing import Any, Optional, Dict, TYPE_CHECKING
import yaml
import bluetooth
import bluetooth._bluetooth as bt
from core.sensor import Sensor
from core import utils
if TYPE_CHECKING:
    # Fix circular imports needed for the type checker
    from core import connection

class SimpleBtSensor(Sensor):
    """Implements a simple scanner that looks for the name of a BT devices given
    their MAC addresses.
    """

    def __init__(self,
                 publishers:Dict[str, 'connection.Connection'],
                 dev_cfg:Dict[str, Any]) -> None:
        """Parses the parameters and prepares to scan for the configured devices.
        dev_cfg:
            - Poll: must be greater than 25
            - AddressX: sequential list of MAC addresses to look for
            - DestinationX: sequential list of destinations to publish ON/OFF to
            when the corresponding Address is found or not. There must be the
            same number of Address and Destination fields.
        Raises:
            - KeyError: when a required parameter doesn't exist
            - ValueError: when the list of Addresses and Destinations don't
            match up or Poll is too small.
        """
        super().__init__(publishers, dev_cfg)

        addr_dest = utils.get_dict_of_sequential_param__output(dev_cfg, "Address", "Destination")
        # bluetooth returns MAC in lower case, make sure our keys are in lower case too
        self.devices = {k.lower() : v for k, v in addr_dest.items()}
        utils.verify_connections_layout(self.comm, self.log, self.name, list(self.devices.values()))

        self.states = dict.fromkeys(list(self.devices.keys()), None)

        if self.poll <= 25:
            raise ValueError("Poll must be more than 25")

        self.log.info("Configured simple BT sensor %s", self.name)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        #configure_output for homie etc. after debug output, so self.comm is clean
        for (mac, destination) in self.devices.items():
            utils.configure_device_channel(self.comm, is_output=True, output_name=destination,
                                           name=f"{mac} available")
        self._register(self.comm)

    def check_state(self) -> None:
        """Loops through the devices and tries to see if they are reachable over
        Bluetooth.
        """
        for address in self.devices:
            result = bluetooth.lookup_name(address, timeout=25)
            self.log.debug("%s scanned for %s, result = %s",
                           self.name, address, result)
            value = "OFF" if result is None else "ON"
            if value != self.states[address]:
                self.states[address] = value
                self._send(value, self.comm, self.devices[address])

    def publish_state(self) -> None:
        """Publishes the last set of states for each device."""
        for address in self.devices:
            state = self.states[address]
            if state is not None:
                self._send(state, self.comm, self.devices[address])
