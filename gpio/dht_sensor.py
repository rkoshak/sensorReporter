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
from configparser import NoOptionError
import board
import adafruit_dht
from core.sensor import Sensor

# Will need to be updated for boards with more or less than 25 digital pins.
# This table should support most Raspberry Pis though.
#PIN_MAP = {"1": board.D1, "2": board.D2, "3": board.D3, "4": board.D4,
#           "5": board.D5, "6": board.D6, "7": board.D7, "8": board.D8,
#           "9": board.D9, "10": board.D10, "11": board.D11, "12": board.D12,
#           "13": board.D13, "14": board.D14, "15": board.D15, "16": board.D16,
#           "17": board.D17, "18": board.D18, "19": board.D19, "20": board.D20,
#           "21": board.D21, "22": board.D22, "23": board.D23, "24": board.D24,
#           "25": board.D25}

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

    def __init__(self, publishers, params):
        super().__init__(publishers, params)

        if self.poll <= 0:
            raise ValueError("A positive polling period is required: {}"
                             .format(self.poll))

        pin = params("Pin")
        #if pin not in PIN_MAP:
        #    raise ValueError("Unsupported pin numerb {}".format(pin))

        sen_type = params("Sensor")
        if sen_type in ("DHT22", "AM2302"):
            self.log.info("Creating DHT22/AM2302 sensor")
            self.sensor = adafruit_dht.DHT22(board.D4)
        elif sen_type == "DHT11":
            self.sensor = adafruit_dht.DHT11(board.D4)
        else:
            raise ValueError("{} is an unsupported Sensor".format(sen_type))

        self.log.info("Sensor created, setting parameters.")
        self.humi_dest = params("HumiDest")
        self.temp_dest = params("TempDest")

        # Default to C. If it's defined and not C or F raises ValueError.
        try:
            self.temp_unit = params("TempUnit")
            if self.temp_unit not in ("C", "F"):
                raise ValueError("{} is an unsupported temp unit".format(self.temp_unit))
        except NoOptionError:
            self.temp_unit = "C"

        try:
            self.smoothing = bool(params("Smoothing"))
        except NoOptionError:
            self.smoothing = False

        if self.smoothing:
            self.humidity_readings = [None] * 5
            self.temp_readings = [None] * 5

        self.publish_state()

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
                self._send("{:.1f}".format(to_send), self.temp_dest)
            else:
                self.log.warning("Unreasonable temperature reading of %s "
                                 "dropping it", temp)

            if humidity and 0 <= humidity <= 100:
                to_send = humidity
                if self.smoothing:
                    self.humidity_readings.pop()
                    self.humidity_readings.insert(0, humidity)
                    to_send = sum([h for h in self.humidity_readings if h]) / 5
                self._send("{:.1f}".format(to_send), self.humi_dest)
            else:
                self.log.warning("Unreasonable humidity reading of %s, "
                                 "dropping it", humidity)

        except RuntimeError as error:
            self.log.warning("Error reading DHT: %s", error.args[0])
