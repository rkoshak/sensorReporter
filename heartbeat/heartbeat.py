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
"""Contains the Heartbeat sensor.

Classes: Heartbeat
"""
import datetime
import yaml
from core.sensor import Sensor
from core.utils import verify_connections_layout

OUT_NUM = "FormatNumber"
OUT_STRING = "FormatString"

class Heartbeat(Sensor):
    """Polling sensor that publishes the current time in number of milliseconds
    since it was started and a string in DD:HH:MM:SS format.
    """

    def __init__(self, publishers, dev_cfg):
        """Expects the following parameters:
        - "Poll": cannot be < 1

        Raises:
        - KeyError - if an expected parameter doesn't exist
        - ValueError - if poll is < 0.
        """
        super().__init__(publishers, dev_cfg)

        self.start_time = datetime.datetime.now()

        if self.poll < 1:
            raise ValueError("Heartbeat requires a poll >= 1")

        verify_connections_layout(self.comm, self.log, self.name, [OUT_NUM, OUT_STRING])
        self.log.info("Configuing Heartbeat %s: interval %s",
                      self.name, self.poll)
        self.log.debug("%s will report to following connections:\n%s",
                       self.name, yaml.dump(self.comm))

    def publish_state(self):
        """Calculates the current up time and publishes it as msec and string
        formats.
        """

        uptime = datetime.datetime.now() - self.start_time
        up_ms = int(uptime.total_seconds() * 1000)
        self._send(str(up_ms), self.comm, OUT_NUM)

        msg = str(uptime)
        #cut last 7 characters, which contain the milliseconds
        self._send(msg[:-7], self.comm, OUT_STRING)
