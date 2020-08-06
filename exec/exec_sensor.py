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

"""Implements a polling sensor that executes a command line script once per
poll and reports the results.
"""
import subprocess
import time
from core.sensor import Sensor
from core.utils import issafe

class ExecSensor(Sensor):
    """Periodically calls a script/program and publishes the result."""

    def __init__(self, publishers, params):
        """Parses the params and prepars to be called. Polling is managed
        outside the sensor.
        """
        super().__init__(publishers, params)

        self.script = params("Script")
        self.destination = params("Destination")
        self.start_time = time.time()

        self.cmd_args = [arg for arg in self.script.split(' ') if issafe(arg)]
        self.results = ""

        self.log.info("Configured exec_sensor to call script %s and destination %s "
                      "with interval %s", self.script, self.destination, self.poll)

    def check_state(self):
        """Calls the script and saves and publishes the result."""
        self.log.debug("Executing with arguments %s", self.cmd_args)

        try:
            self.results = subprocess.check_output(self.cmd_args, shell=False,
                                                   universal_newlines=True,
                                                   timeout=self.poll).rstrip()
            self.log.info("Command results to be published to %s\n%s",
                          self.destination, self.results)
        except subprocess.CalledProcessError as ex:
            self.log.error("Command returned an error code %s\n%s", ex.returncode,
                           ex.output)
        except subprocess.TimeoutExpired:
            self.log.error("Command took longer than %d to complete!", self.poll)
            self.results = "ERROR"

        self.publish_state()

    def publish_state(self):
        """Publishes the most recent results from the script."""
        self._send(self.results, self.destination)
