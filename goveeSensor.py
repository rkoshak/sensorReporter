"""
   Copyright 2020 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: goveeSensor.py
 Author: Rich Koshak
 Date:   July 2, 2020
 Purpose: Detects and publishes Govee BT temp/humi sensor readings.

 The code is based on https://github.com/Thrilleratplay/GoveeWatcher.
"""

import sys
from bleson import get_provider, Observer, UUID16
from bleson.logger import log, set_level, ERROR, DEBUG

# Disable warnings
set_level(ERROR)

class goveeSensor:
    """Listens for Govee temp/humi sensor BT broadcasts and publishes them."""

    def __init__(self, publisher, logger, params, sensors, actuators):
        """Initializes the listener and kicks off the listening"""

        self.logger = logger
        self.dest_root = params("Destination")
        self.publish = publisher

        self.logger.info('----------Configuring Govee listener with destination {}'.format(self.dest_root))

        self.GOVEE_BT_MAC_PREFIX = "A4:C1:38"
        self.H5075_UPDATE_UUID16 = UUID16(0xEC88)

        self.adapter = get_provider().get_adapter()
        self.observer = Observer(self.adapter)
        self.observer.on_advertising_data = self.on_advertisement
        self.observer.start()
        self.poll = -1
        self.devices = {}

    def on_advertisement(self, advertisement):
        self.logger.info("Received advertisement from {}".format(advertisement.address.address))

        if advertisement.address.address.startswith(self.GOVEE_BT_MAC_PREFIX):
            self.logger.info("Received Govee advertisement")

            mac = advertisement.address.address

            if self.H5075_UPDATE_UUID16 in advertisement.uuid16s:
                name = advertisement.name.split("'")[1]
                if mac not in self.devices:
                    self.devices[mac] = name
                encoded_data = int(advertisement.mfg_data.hex()[6:12], 16)
                battery = int(advertisement.mfg_data.hex()[12:14], 16)
                temp_c = format((encoded_data / 10000), ".2f")
                temp_f = format((((encoded_data / 10000) * 1.8) + 32), ".2f")
                humi = format(((encoded_data % 1000) / 10), ".2f")

                self.logger.info("Govee data to publish: name = {}, "
                                 "battery = {}, temp_c = {}, temp_f = {}, and "
                                 "humi = {}"
                                 .format(name, battery, temp_c, temp_f, humi))
                for conn in self.publish:
                    conn.publish(str(battery),
                                 "{}/{}/battery".format(self.dest_root, name))
                    conn.publish(str(temp_c),
                                 "{}/{}/temp_C".format(self.dest_root, name))
                    conn.publish(str(temp_f),
                                 "{}/{}/temp_f".format(self.dest_root, name))
                    conn.publish(str(humi),
                                 "{}/{}/humi".format(self.dest_root, name))

            if advertisement.rssi is not None and advertisement.rssi != 0:
                if mac in self.devices:
                    for conn in self.publish:
                        conn.publish(str(advertisement.rssi),
                                     "{}/{}/rssi"
                                     .format(self.dest_root, self.devices[mac]))

    def checkState(self):
        """Does nothing"""

    def publishState(self):
        """Does nothing"""

    def cleanup(self):
        """Stop the observer"""

        self.logger.info("Stopping Govee observer")
        self.oberver.stop()
