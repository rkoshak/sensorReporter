import time
import board
import busio
import adafruit_ahtx0
import yaml
import json
from core.sensor import Sensor
from core.utils import verify_connections_layout, configure_device_channel, ChanType
from decimal import Decimal, ROUND_HALF_UP

class AHT20Sensor(Sensor):
    """A polling sensor that reads and reports temperature and humidity using the AHT20 sensor.

    Parameters:
        - Poll: must be > 0
        - TempUnit: optional parameter, one of "C" or "F", defaults to "C"
        - Smoothing: optional parameter, if True the average of the last five readings is published,
          when False only the most recent is published.
        - TempDecimals: optional parameter, number of decimal places to round temperature to, defaults to 1
        - HumDecimals: optional parameter, number of decimal places to round humidity to, defaults to 1
    
    Raises:
        - KeyError: if a required parameter is not present
        - ValueError: if a parameter has an unusable value
        - ValueError: if TempUnit is not "C" or "F"
        - ValueError: if Decimals is not a positive integer
        - RuntimeError: if there is a problem connecting to the sensor
    """

    def __init__(self, publishers, dev_cfg):
  
        super().__init__(publishers, dev_cfg)

        if self.poll <= 0:
            raise ValueError("A positive polling period is required: " + str(self.poll))

        # Default to C. If it's defined and not C or F raises ValueError.
        self.temp_unit = dev_cfg.get("TempUnit", "C")
        if self.temp_unit not in ("C", "F"):
            raise ValueError(self.temp_unit + " is an unsupported temp unit")

        self.smoothing = dev_cfg.get("Smoothing", False)
        if self.smoothing:
            self.temp_readings = [None] * 5

        # Decimals for temperature and humidity
        self.temp_decimals = dev_cfg.get("TempDecimals", 1)
        self.hum_decimals = dev_cfg.get("HumDecimals", 1)

        bad_values = [val for val in [self.temp_decimals, self.hum_decimals] if val < 0]

        if bad_values:
            raise ValueError(f"Decimals must be a positive integer. Invalid value(s): {bad_values}")
        

        # Initialize I2C and sensor for Raspberry Pi
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        self.sensor = adafruit_ahtx0.AHTx0(self.i2c)

        # Verify configured connections
        verify_connections_layout(self.comm, self.log, self.name)
        self.log.info("Sensor %s created, setting parameters.", self.name)
        self.log.debug("%s will report to following connections:\n%s", self.name, yaml.dump(self.comm))

        # Configure output channel
        configure_device_channel(self.comm, is_output=True, datatype=ChanType.STRING, name="sensor_readings")
        self._register(self.comm)

    def _round_half_up(self, value:float, decimals:int) -> float:
        """Rounds a float to the nearest half up."""
        factor = Decimal("1." + "0" * decimals)  # Equivalent to 10^(-decimals)
        return float(Decimal(value).quantize(factor, rounding=ROUND_HALF_UP))

    def read_sensor_data(self):
        """Reads temperature and humidity data from the sensor."""
        temp = self.sensor.temperature
        humidity = self.sensor.relative_humidity

        if self.temp_unit == "F":
            temp = temp * (9 / 5) + 32
        
        return self._round_half_up(temp, self.temp_decimals), self._round_half_up(humidity, self.hum_decimals)


    def publish_state(self):
        """Acquires the current readings and publishes as a JSON string."""
        try:
            temp, humidity = self.read_sensor_data()

            # Check if the readings are within the 'Scope of Work' specified in the datasheet
            if -40 <= temp <= 85 and 0 <= humidity <= 100:
                to_send_temp = temp
                
                if self.smoothing:
                    self.temp_readings.pop()
                    self.temp_readings.insert(0, temp)
                    to_send_temp = sum([t for t in self.temp_readings if t]) / 5

                sensor_data = {
                    "temperature": to_send_temp,
                    "temperature_unit": self.temp_unit,
                    "humidity": humidity
                }

                json_payload = json.dumps(sensor_data)
                self._send(json_payload, self.comm)
            else:
                self.log.warning("%s unreasonable readings (Temp: %s, Humidity: %s), dropping it",
                                 self.name, temp, humidity)
        except RuntimeError as error:
            self.log.warning("%s error reading AHT20: %s", self.name, error.args[0])
