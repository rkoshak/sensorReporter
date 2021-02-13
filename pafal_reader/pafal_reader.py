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
from pafal_reader.energymeter import pafalConnector
import sys

_SERIAL_DEVICE_DEFAULT = "/dev/ttyUSB0"


class PafalReader(Sensor):
    """Polling sensor that publishes current values of the attached
    smart meter.
    """

    def __init__(self, publishers, params):
        """Expects the following parameters:
        - "Bezug": ddd
        - "Lieferung": ddd
        - "Poll": cannot be < 60
        - "SerialDevice": the serial device to read from

        Raises:
        - NoOptionError - if an expected parameter doesn't exist
        - ValueError - if poll is < 0.
        """
        super().__init__(publishers, params)

        self.dst_bezug = params("Bezug_Dst")
        self.dst_lieferung = params("Lieferung_Dst")
        self.serdevstring = params("SerialDevice")

        if self.poll < 60:
            raise ValueError("PafalReader requires a poll >= 60")

        self.serdev = pafalConnector( logger = self.log, devicePort=self.serdevstring )

        self.log.info("Configuring PafalReader: Bezug to %s and Lieferung to %s with "
                      "interval %s, %i publishers", self.dst_bezug, self.dst_lieferung, self.poll, len(publishers))

    def publish_state(self):
        """Collects data from Pafal and publishes it.
        """

        # 0.0.0 -> Smart Meter No
        # 0.2.0 -> Firmware
        # 1.8.0*00 -> Bezug
        # 2.8.0*00 -> Lieferung
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

        self.log.debug("Successful read from Pafal. Smart Meter '{num}' with firmware '{fw}'."
            "Bezug {bezug}, Lieferung {liefer}".format(
                num = result.get("0.0.0", "<not available>"),
                fw = result.get("0.2.0", "<not available>"),
                bezug = "<not available>" if result.get("1.8.0*00", None) is None else "{:.3f}".format(result["1.8.0*00"]),
                liefer = "<not available>" if result.get("2.8.0*00", None) is None else "{:.3f}".format(result["2.8.0*00"])
            ))

        if not result.get("1.8.0*00", None) is None:
            self._send(str(result["1.8.0*00"]), self.dst_bezug)
        
        if not result.get("2.8.0*00", None) is None:
            self._send(str(result["2.8.0*00"]), self.dst_lieferung)
