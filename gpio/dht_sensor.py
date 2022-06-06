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
"""Contains DhtSensor, a sensor that reads DHT11, DHT22 or AM2302 temp/humi
sensors. Reading of the sensor is accomplished using the adafruit_dht library.
"""
import yaml
import board
import adafruit_dht
from core.sensor import Sensor
from core.utils import verify_connections_layout, configure_device_channel, ChanType

OUT_TEMP = "Temperature"
OUT_HUMID = "Humidity"

class DhtSensor(Sensor):
    """A polling sensor that reads and reports temperature and humidity. It
    supports DHT22, AM2302, and DHT11 sensors. It requires a poll > 0.
    Parameters:
        "Pin" : the data pin the sensor is connected to
        "Sensor": one of "DHT22", "DHT11", "AM2302". It must match the sensor
        type.
        "HumiDest": destination for the humidity reading
        "TempDest": destination for the temp reading
        "TempUnit": optional, one of "C" or "F", units the temp is published,
        defaults to "C"
        "Smoothing": optional parameter, when True it will publish the average
        of the last five readings instead of just the current reading.

    Raises:
        NoOptionError when a required options is not present.
        ValueError when a parameter has an unsupported value.
    """

    def __init__(self, publishers, dev_cfg):
        """Initialize the DHT sensor and collect the first reading.
        Parameters:
            - Poll: must be > 0
            - Pin: GPIO pin where the data pin of the sensor is wired, BMC
            numbering
            - Sensor: one of "DHT11", "DHT22" or "AM2302"
            - TempUnit: optional parameter, one of "C" or "F", defaults to "C"
            - Smoothing: optional parameter, if True the average of the last
            five readings is published, when False only the most recent is
            published.
        Raises
            - KeyError: if a required parameter is not present
            - ValueError: if a parameter has an unsuable value
            - RuntimeError: if there is a problem connecting to the sensor:w

        """
        super().__init__(publishers, dev_cfg)

        if self.poll <= 0:
            raise ValueError("A positive polling period is required: {}"
                             .format(self.poll))

        pin = dev_cfg["Pin"]
        bpin = None
        pin_name = "D{}".format(pin)
        if hasattr(board, pin_name):
            bpin = getattr(board, pin_name)
        else:
            raise ValueError("Unsupported pin number {}".format(pin))

        sen_type = dev_cfg["Sensor"]
        if sen_type in ("DHT22", "AM2302"):
            self.log.info("Creating DHT22/AM2302 sensor")
            self.sensor = adafruit_dht.DHT22(bpin)
        elif sen_type == "DHT11":
            self.sensor = adafruit_dht.DHT11(bpin)
        else:
            raise ValueError("{} is an unsupported Sensor".format(sen_type))

        verify_connections_layout(self.comm, self.log, self.name, [OUT_TEMP, OUT_HUMID])
        self.log.info("Sensor %s created, setting parameters.", self.name)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        # Default to C. If it's defined and not C or F raises ValueError.
        self.temp_unit = dev_cfg.get("TempUnit", "C")
        if self.temp_unit not in ("C", "F"):
            raise ValueError("{} is an unsupported temp unit".format(self.temp_unit))

        self.smoothing = dev_cfg.get("Smoothing", False)

        if self.smoothing:
            self.humidity_readings = [None] * 5
            self.temp_readings = [None] * 5

        self.publish_state()

        #configure_output for homie etc. after debug output, so self.comm is clean
        configure_device_channel(self.comm, is_output=True, output_name=OUT_TEMP,
                                 datatype=ChanType.FLOAT, name="temperatur reading",
                                 unit='°C' if self.temp_unit=='C' else '°F')
        configure_device_channel(self.comm, is_output=True, output_name=OUT_HUMID,
                                 datatype=ChanType.FLOAT, name="humidity reading", unit='%')
        self._register(self.comm)

    def publish_state(self):
        """Acquires the current reading. If the value is reasonable (humidity
        between 0 and 100, temp between -40 and 125) the reading is published.
        If smoothing, the average of the most recent five readings is published.
        If not smoothing the current reading is published. If temp_unit is "F",
        the temp is published in degrees F. Both temp and humidity are rounded
        to the tenth's place.
        Warning log statements are written for unreasonable values or errors
        reading the sensor.
        """
        try:
            temp = self.sensor.temperature
            if temp and self.temp_unit == "F":
                temp = temp * (9 / 5) + 32

            humidity = self.sensor.humidity

            if temp and -40 <= temp <= 125:
                to_send = temp
                if self.smoothing:
                    self.temp_readings.pop()
                    self.temp_readings.insert(0, temp)
                    to_send = sum([t for t in self.temp_readings if t]) / 5
                self._send("{:.1f}".format(to_send), self.comm, OUT_TEMP)
            else:
                self.log.warning("%s unreasonable temperature reading of %s "
                                 "dropping it", self.name, temp)

            if humidity and 0 <= humidity <= 100:
                to_send = humidity
                if self.smoothing:
                    self.humidity_readings.pop()
                    self.humidity_readings.insert(0, humidity)
                    to_send = sum([h for h in self.humidity_readings if h]) / 5
                self._send("{:.1f}".format(to_send), self.comm, OUT_HUMID)
            else:
                self.log.warning("%s unreasonable humidity reading of %s, "
                                 "dropping it", self. name, humidity)

        except RuntimeError as error:
            self.log.warning("%s error reading DHT: %s", self.name, error.args[0])
