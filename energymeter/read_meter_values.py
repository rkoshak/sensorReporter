# Copyright 2021 Alexander Behring
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
"""Contains the Pafal reader sensor.

Classes: PafalReader
"""
from core.sensor import Sensor
from energymeter.em_connections import Pafal20ec3grConnector
import sys


class Pafal20ec3gr(Sensor):
    """Polling sensor that publishes current values of the attached
    energy meter.
    """

    def __init__(self, publishers, params):
        """Expects the following parameters:
        - "Import_Dst": Destination for import value
        - "Export_Dst": Destination for export value
        - "Poll": cannot be < 60
        - "SerialDevice": the serial device file to read from

        Raises:
        - NoOptionError - if an expected parameter doesn't exist
        - ValueError - if poll is < 0.
        """
        super().__init__(publishers, params)

        self.dst_import = params("Import_Dst")
        self.dst_export = params("Export_Dst")
        self.serdevstring = params("SerialDevice")

        if self.poll < 60:
            raise ValueError("PafalReader requires a poll >= 60")

        self.serdev = Pafal20ec3grConnector( logger = self.log, devicePort=self.serdevstring )

        self.log.info("Configuring PafalReader: import to %s and export to %s with "
                      "interval %s, %i publishers", self.dst_import, self.dst_export, self.poll, len(publishers))

    def publish_state(self):
        """Collects data from Pafal and publishes it.
        """

        # 0.0.0 -> Energy Meter No
        # 0.2.0 -> Firmware
        # 1.8.0*00 -> Import
        # 2.8.0*00 -> Export
        try:
            result = self.serdev.readData( {
                "0.0.0": [False],
                "0.2.0": [False],
                "1.8.0*00": [True],
                "2.8.0*00": [True]
            } )
        except Exception as inst:
            self.log.error("Error '{ERR}' retrieving value from Pafal. Details: {DET}.".format( 
                ERR = str(sys.exc_info()[0]),
                DET = str(inst)
                ))
            result = None

        if result is None:
            # Try again next cycle with fresh connection
            self.serdev.close()
            return

        if (len(result) == 0):
            # Nothing read...
            return

        self.log.debug("Successful read from Pafal. Energy meter '{num}' with firmware '{fw}'."
            "Import {bezug}, Export {liefer}".format(
                num = result.get("0.0.0", "<not available>"),
                fw = result.get("0.2.0", "<not available>"),
                bezug = "<not available>" if result.get("1.8.0*00", None) is None else "{:.3f}".format(result["1.8.0*00"]),
                liefer = "<not available>" if result.get("2.8.0*00", None) is None else "{:.3f}".format(result["2.8.0*00"])
            ))

        if not result.get("1.8.0*00", None) is None:
            self._send(str(result["1.8.0*00"]), self.dst_import)
        
        if not result.get("2.8.0*00", None) is None:
            self._send(str(result["2.8.0*00"]), self.dst_export)

    def cleanup(self):
        """Called when shutting down the sensor, give it a chance to clean up
        and release resources."""
        self.log.info("Disconnecting from serial device")
        self.serdev.close()