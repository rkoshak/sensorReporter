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

""" Implements a polling sensor that executes a command line script once per
    poll and reports the results.
"""
import subprocess
from typing import Any, Dict, TYPE_CHECKING
import time
import yaml
from core.sensor import Sensor
from core import utils
if TYPE_CHECKING:
    # Fix circular imports needed for the type checker
    from core import connection

class ExecSensor(Sensor):
    """ Periodically calls a script/program and publishes the result."""

    def __init__(self,
                 publishers:Dict[str, 'connection.Connection'],
                 dev_cfg:Dict[str, Any]) -> None:
        """ Parses the dev_cfg and prepares to be called. Polling is managed
            outside the sensor.
        """
        super().__init__(publishers, dev_cfg)

        self.script = dev_cfg["Script"]
        self.start_time = time.time()

        self.cmd_args = [arg for arg in self.script.split(' ') if utils.issafe(arg)]
        self.results = ""

        self.log.info("Configured exec_sensor %s to call script '%s' at interval %s ",
                      self.name, self.script, self.poll)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

        #configure_output for homie etc. after debug output, so self.comm is clean
        utils.configure_device_channel(self.comm, is_output=True,
                                       name="Result of sensor script")
        self._register(self.comm)

    def check_state(self) -> None:
        """ Calls the script and saves and publishes the result."""
        self.log.debug("%s executed with arguments %s", self.name, self.cmd_args)

        try:
            self.results = subprocess.check_output(self.cmd_args, shell=False,
                                                   universal_newlines=True,
                                                   timeout=self.poll).rstrip()
            self.log.info("%s command results %s",
                          self.name, self.results)
        except subprocess.CalledProcessError as ex:
            self.log.error("%s command returned an error code %s\n%s",
                           self.name, ex.returncode, ex.output)
        except subprocess.TimeoutExpired:
            self.log.error("%s command took longer than %d to complete!",
                           self.name, self.poll)
            self.results = "ERROR"

        self.publish_state()

    def publish_state(self) -> None:
        """ Publishes the most recent results from the script."""
        self._send(self.results, self.comm)
