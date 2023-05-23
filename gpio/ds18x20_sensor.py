# Copyright 2022 Florian Hotze
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

"""Contains Ds18x20Sensor, a sensor that reads DS18S20 or DS18B20 1-Wirebus temp sensors.
Reading of the sensor is accomplished using the system's 1-Wire bus driver.
Note that the 1-Wire bus must be enabled on the system to use this sensor.
"""
import os
import yaml
from core.sensor import Sensor
from core.utils import verify_connections_layout, configure_device_channel, ChanType

# constants
OUT_TEMP = "Temperature"
BASE_DIR = '/sys/bus/w1/devices/'
SLAVE_FILE = '/w1_slave'

class Ds18x20Sensor(Sensor):
    """A polling sensor that reads and reports temperature. It supports DS18S20
    and DS18B20 1-Wire sensors. It requires a poll > 0.

    Parameters:
            - Poll: must be > 0
            - Mac: the device address of the sensor on the 1-Wire bus
            - TempUnit: optional parameter, one of "C" or "F", defaults to "C"
            - Smoothing: optional parameter, if True the average of the last
            five readings is published, when False only the most recent is
            published.

    Raises:
        - KeyError: if a required parameter is not present
        - ValueError: if a parameter has an unsuable value
        - RuntimeError: if there is a problem connecting to the sensor
    """

    def __init__(self, publishers, dev_cfg):
        """Initialize the DS18x20 sensor.

        Parameters:
            - Poll: must be > 0
            - Mac: the device address of the sensor on the 1-Wire bus
            - TempUnit: optional parameter, one of "C" or "F", defaults to "C"
            - Smoothing: optional parameter, if True the average of the last
            five readings is published, when False only the most recent is
            published.

        Raises:
            - KeyError: if a required parameter is not present
            - ValueError: if a parameter has an unusuable value
        """

        super().__init__(publishers, dev_cfg)

        if self.poll <= 0:
            raise ValueError("A positive polling period is required: " + self.poll)

        self.mac = dev_cfg["Mac"]
        os.system("modprobe w1-gpio")
        os.system("modprobe w1-therm")

        verify_connections_layout(self.comm, self.log, self.name, OUT_TEMP)
        self.log.info("Sensor %s created, setting parameters.", self.name)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        # Default to C. If it's defined and not C or F raises ValueError.
        self.temp_unit = dev_cfg.get("TempUnit", "C")
        if self.temp_unit not in ("C", "F"):
            raise ValueError(self.temp_unit + " is an unsupported temp unit")

        self.smoothing = dev_cfg.get("Smoothing", False)

        if self.smoothing:
            self.temp_readings = [None] * 5

        # Configure_output for homie etc. after debug output, so self.comm is clean
        configure_device_channel(self.comm, is_output=True, output_name=OUT_TEMP,
                                 datatype=ChanType.FLOAT, name="temperatur reading",
                                 unit="°" + self.temp_unit)
        self._register(self.comm)

    def publish_state(self):
        """Acquires the current reading. If the value is reasonable (temp between
        -40 and 125) the reading is published.
        If smoothing, the average of the most recent five readings is published.
        If not smoothing the current reading is published. If temp_unit is "F",
        the temp is published in degrees F.
        Warning log statements are written for unreasonable values or errors
        reading the sensor.

        Raises:
            - RuntimeError: if there is a problem connecting to the sensor
        """
        try:
            # Read 1-Wire slave file
            file = open(BASE_DIR + self.mac + SLAVE_FILE, mode="r", encoding="utf-8")
            lines = file.readlines()
            file.close()
            # Read and convert temp value
            temp_pos = lines[1].find("t=")
            temp = float(lines[1][temp_pos + 2:]) / 1000
            if temp and self.temp_unit == "F":
                temp = temp * (9 / 5) + 32

            if temp and -55 <= temp <= 125:
                to_send = temp
                if self.smoothing:
                    self.temp_readings.pop()
                    self.temp_readings.insert(0, temp)
                    to_send = sum([t for t in self.temp_readings if t]) / 5
                self._send(to_send, self.comm, OUT_TEMP)
            else:
                self.log.warning("%s unreasonable temperature reading of %s "
                                 "dropping it", self.name, temp)

        except RuntimeError as error:
            self.log.warning("%s error reading DS18x20: %s", self.name, error.args[0])
