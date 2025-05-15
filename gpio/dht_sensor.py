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
""" Contains DhtSensor, a sensor that reads DHT11, DHT22 or AM2302 temp/humi
    sensors. Reading of the sensor is accomplished using the adafruit_dht library.
"""
from typing import Any, Dict, TYPE_CHECKING
import yaml
import board
import adafruit_dht
from core.sensor import Sensor
from core import utils
if TYPE_CHECKING:
    # Fix circular imports needed for the type checker
    from core import connection

OUT_TEMP = "Temperature"
OUT_HUMID = "Humidity"

class DhtSensor(Sensor):
    """ A polling sensor that reads and reports temperature and humidity.
        It supports DHT22, AM2302, and DHT11 sensors. It requires a poll > 0.
        Parameters:
            "Pin"       : the data pin the sensor is connected to
            "Sensor"    : one of "DHT22", "DHT11", "AM2302".
                          It must match the sensor type.
            "HumiDest"  : destination for the humidity reading
            "TempDest"  : destination for the temp reading
            "TempUnit"  : optional, one of "C" or "F",
                          unit the temp is published, defaults to "C"
            "Smoothing" : optional parameter, when True or >=2 it will publish the average
                          of the last readings instead of just the current reading.

        Raises:
            NoOptionError : when a required options is not present.
            ValueError    : when a parameter has an unsupported value.
    """

    def __init__(self,
                 publishers:Dict[str, 'connection.Connection'],
                 dev_cfg:Dict[str, Any]) -> None:
        """ Initialize the DHT sensor and collect the first reading.
            Parameters:
                - Poll      : must be > 0
                - Pin       : GPIO pin where the data pin of the sensor is wired,
                              BMC numbering
                - Sensor    : one of "DHT11", "DHT22" or "AM2302"
                - TempUnit  : optional parameter, one of "C" or "F", defaults to "C"
                - Smoothing : optional parameter, if True or >= 2 the average of the last
                              readings is published, when False only
                              the most recent is published.
            Raises
                - KeyError     : if a required parameter is not present
                - ValueError   : if a parameter has an unusable value
                - RuntimeError : if there is a problem connecting to the sensor:w
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

        utils.verify_connections_layout(self.comm, self.log, self.name, [OUT_TEMP, OUT_HUMID])
        self.log.info("Sensor %s created, setting parameters.", self.name)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        # Default to C. If it's defined and not C or F raises ValueError.
        self.temp_unit = dev_cfg.get("TempUnit", "C")
        if self.temp_unit not in ("C", "F"):
            raise ValueError("{} is an unsupported temperature unit".format(self.temp_unit))

        smoothing = dev_cfg.get("Smoothing", 1)
        if smoothing is True:
            # Value 3 equals approximately moving average over the last 5 readings
            self.smoothing = 3
        elif smoothing is False or smoothing < 1:
            # For value 1 the exponential smoothing algorithm will equal the current reading
            self.smoothing = 1
        else:
            self.smoothing = int(smoothing)

        self.humidity_average = 0.0
        self.temp_average = 0.0
        self.smoothing_divider = 1

        self.publish_state()

        #configure_output for homie etc. after debug output, so self.comm is clean
        utils.configure_device_channel(self.comm, is_output=True, output_name=OUT_TEMP,
                                       datatype=utils.ChanType.FLOAT, name="temperature reading",
                                       unit='°C' if self.temp_unit=='C' else '°F')
        utils.configure_device_channel(self.comm, is_output=True, output_name=OUT_HUMID,
                                       datatype=utils.ChanType.FLOAT,
                                       name="humidity reading", unit='%')
        self._register(self.comm)

    def publish_state(self) -> None:
        """ Acquires the current reading. If the value is reasonable (humidity
            between 0 and 100, temp between -40 and 125) the reading is published.

            If smoothing, the average of the last readings is published.
            If not smoothing the current reading is published.
            If temp_unit is "F", the temp is published in degrees F.
            Both temp and humidity are rounded to the tenth's place.

            Warning log statements are written for unreasonable values or errors
            reading the sensor.
        """
        try:
            temp = self.sensor.temperature
            if temp and self.temp_unit == "F":
                temp = temp * (9 / 5) + 32

            humidity = self.sensor.humidity

            denominator = self.smoothing_divider
            numerator = denominator - 1

            if temp and -40 <= temp <= 125:
                # apply exponential smoothing for the temperature
                weighted_temp = self.temp_average * numerator
                to_send = self.temp_average = (weighted_temp + temp) / denominator

                self._send("{:.1f}".format(to_send), self.comm, OUT_TEMP)
            else:
                self.log.warning("%s unreasonable temperature reading of %s "
                                 "dropping it", self.name, temp)

            if humidity and 0 <= humidity <= 100:
                # apply exponential smoothing for the humidity
                weighted_humid = self.humidity_average * numerator
                to_send = self.humidity_average = (weighted_humid + humidity) / denominator

                self._send("{:.1f}".format(to_send), self.comm, OUT_HUMID)
            else:
                self.log.warning("%s unreasonable humidity reading of %s, "
                                 "dropping it", self. name, humidity)
            self.log.debug("%s read temperature %d%s (smoothed %d%s), "
                           "humidity %d%% (smoothed %d%%)",
                           self.name, temp, self.temp_unit, self.temp_average, self.temp_unit,
                           humidity, self.humidity_average)

            if self.smoothing_divider < self.smoothing:
                self.smoothing_divider = self.smoothing_divider + 1

        except RuntimeError as error:
            self.log.warning("%s error reading DHT: %s", self.name, error.args[0])
