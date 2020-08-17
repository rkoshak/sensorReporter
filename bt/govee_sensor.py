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

"""Implements a BTLE listener that looks for broadcasts from a Govee H5072
sensor (it may work with others).
"""
from bleson import get_provider, Observer, UUID16
from bleson.logger import set_level, ERROR#, DEBUG
from core.sensor import Sensor

# Disable bleson warning messages in the log.
set_level(ERROR)
#set_level(DEBUG)

GOVEE_BT_MAC_PREFIX = "A4:C1:38"
H5075_UPDATE_UUID16 = UUID16(0xEC88)

class GoveeSensor(Sensor):
    """Listens for Govee temp/humi sensor BTLE broadcases and publishes them."""

    def __init__(self, publishers, params):
        """Initializes the listener and kicks off the listening thread."""
        super().__init__(publishers, params)

        self.dest_root = params("Destination")

        self.log.info("Configuring Govee listener with destination %s",
                      self.dest_root)

        self.adapter = get_provider().get_adapter()
        self.observer = Observer(self.adapter)
        self.observer.on_advertising_data = self.on_advertisement
        self.observer.start()

        # Store readings so they can be reported on demand.
        self.devices = {}

    def on_advertisement(self, advertisement):
        """Called when a BTLE advertisement is received. If it goes with one
        of the Govee H5075 sensors, the reading is parsed and published."""
        self.log.debug("Received advertisement from %s",
                       advertisement.address.address)

        if advertisement.address.address.startswith(GOVEE_BT_MAC_PREFIX):
            self.log.debug("Received Govee advertisement")

            mac = advertisement.address.address

            # Process a sensor reading.
            if H5075_UPDATE_UUID16 in advertisement.uuid16s:
                split = advertisement.name.split("'")

                name = split[0] if len(split) == 1 else split[1]
                if mac not in self.devices:
                    self.devices[mac] = {}
                    self.devices[mac]["name"] = name

                encoded_data = int(advertisement.mfg_data.hex()[6:12], 16)
                self.devices[mac]["battery"] = int(advertisement.mfg_data.hex()[12:14],
                                                   16)
                self.devices[mac]["temp_c"] = format((encoded_data / 10000), ".2f")
                self.devices[mac]["temp_f"] = format((((encoded_data / 10000) * 1.8) + 32),
                                                     ".2f")
                self.devices[mac]["humi"] = format(((encoded_data % 1000) / 10),
                                                   ".2f")

                self.log.debug("Govee data to publish: %s", self.devices)
                self.publish_state()

            # Process an rssi reading. Don't bother to publish now, wait for the
            # next sensor reading.
            if advertisement.rssi is not None and advertisement.rssi != 0:
                # Ignore rssi from devices that haven't reported a sensor
                # reading yet.
                if mac in self.devices:
                    self.devices[mac]["rssi"] = advertisement.rssi

    def publish_state(self):
        """Publishes the most recent of all the readings."""

        for conn in self.publishers:
            for mac in self.devices:
                if "name" in self.devices[mac]:
                    name = self.devices[mac]["name"]
                    dest = "{}/{}".format(self.dest_root, name)
                    for dev in [dev for dev in self.devices[mac] if dev != "name"]:
                        conn.publish(str(self.devices[mac][dev]),
                                     "{}/{}".format(dest, dev))

    def cleanup(self):
        """Stop the observer."""
        self.log.info("Stopping Govee observer")
        self.observer.stop()
