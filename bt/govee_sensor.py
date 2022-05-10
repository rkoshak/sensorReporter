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
import yaml
from bleson import get_provider, Observer, UUID16, BDAddress
from bleson.logger import set_level, ERROR#, DEBUG
from core.sensor import Sensor
from core.utils import verify_connections_layout, configure_device_channel

# Disable bleson warning messages in the log.
set_level(ERROR)
#set_level(DEBUG)

GOVEE_BT_MAC_PREFIX = "A4:C1:38"
H5075_UPDATE_UUID16 = UUID16(0xEC88)

OUT_NAME = "DeviceName"
OUT_BATTERY = "Battery"
OUT_TEMP = "Temperature"
OUT_HUMID = "Humidity"
OUT_RSSI = "RSSI"

class GoveeSensor(Sensor):
    """Listens for Govee temp/humi sensor BTLE broadcases and publishes them."""

    def __init__(self, publishers, dev_cfg):
        """Initializes the listener and kicks off the listening thread."""
        super().__init__(publishers, dev_cfg)

        self.mac = BDAddress(dev_cfg["Address"])

        # Default to C. If it's defined and not C or F raises ValueError.
        self.temp_unit = dev_cfg.get("TempUnit", "C")
        if self.temp_unit not in ("C", "F"):
            raise ValueError(f"{self.temp_unit} is an unsupported temperature unit")

        self.log.info("Configuring Govee listener %s for BT MAC %s",
                      self.name, self.mac.address)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        if not self.mac.address.startswith(GOVEE_BT_MAC_PREFIX):
            self.log.warning("%s Address doesn't start with expected prefix %s",
                             self.name, GOVEE_BT_MAC_PREFIX)

        verify_connections_layout(self.comm, self.log, self.name,
                                  [OUT_NAME, OUT_BATTERY, OUT_TEMP,
                                   OUT_HUMID, OUT_RSSI])

        self.adapter = get_provider().get_adapter()
        self.observer = Observer(self.adapter)
        self.observer.on_advertising_data = self.on_advertisement
        self.observer.start()

        # Store readings so they can be reported on demand.
        self.state = {}

        #configure_output for homie etc. after debug output, so self.comm is clean
        configure_device_channel(self.comm, is_output=True, output_name=OUT_NAME,
                                 name="device name")
        configure_device_channel(self.comm, is_output=True, output_name=OUT_BATTERY,
                                 datatype="INTEGER", name="battery level")
        configure_device_channel(self.comm, is_output=True, output_name=OUT_TEMP,
                                 datatype="FLOAT", name="temperature reading",
                                 unit='°C' if self.temp_unit=='C' else '°F')
        configure_device_channel(self.comm, is_output=True, output_name=OUT_HUMID,
                                 datatype="FLOAT", name="humidity reading", unit='%')
        configure_device_channel(self.comm, is_output=True, output_name=OUT_RSSI,
                                 datatype="INTEGER", name="signal strength")
        self._register(self.comm)

    def on_advertisement(self, advertisement):
        """Called when a BTLE advertisement is received. If it goes with one
        of the Govee H5075 sensors, the reading is parsed and published."""
        self.log.debug("%s received advertisement: MAC %s, DeviceName %s",
                       self.name, advertisement.address.address, advertisement.name)

        if advertisement.address == self.mac:
            self.log.debug("%s received Govee advertisement", self.name)

            # Process a sensor reading.
            if H5075_UPDATE_UUID16 in advertisement.uuid16s:
                split = advertisement.name.split("'")

                name = split[0] if len(split) == 1 else split[1]
                self.state[OUT_NAME] = name

                encoded_data = int(advertisement.mfg_data.hex()[6:12], 16)
                self.state[OUT_BATTERY] = str(int(advertisement.mfg_data.hex()[12:14], 16))
                self.state[OUT_TEMP] = format((encoded_data / 10000), ".2f")
                if self.temp_unit == "F":
                    self.state[OUT_TEMP] = format((((encoded_data / 10000) * 1.8) + 32),
                                                     ".2f")
                self.state[OUT_HUMID] = format(((encoded_data % 1000) / 10),
                                                   ".2f")

                self.log.debug("%s govee data to publish: %s", self.name,
                               yaml.dump(self.state))
                self.publish_state()

            # Process an rssi reading. Don't bother to publish now, wait for the
            # next sensor reading.
            if advertisement.rssi is not None and advertisement.rssi != 0:
                # Ignore rssi from state that haven't reported a sensor
                # reading yet.
                self.state[OUT_RSSI] = str(advertisement.rssi)

    def publish_state(self):
        """Publishes the most recent of all the readings."""
        for (key, value) in self.state.items():
            self._send(value, self.comm, key)

    def cleanup(self):
        """Stop the observer."""
        self.log.info("Stopping Govee observer")
        self.observer.stop()
