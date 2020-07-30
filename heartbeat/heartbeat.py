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
import sys
import time
from core.sensor import Sensor
from configparser import NoOptionError

class Heartbeat(Sensor):
    """Polling sensor that publishes the current time in number of milliseconds
    since it was started and a string in DD:HH:MM:SS format.
    """

    def __init__(self, publishers, log, params):
        """Expects the following parameters:
        - "Num-Dest": destination to publish the msec value
        - "Str-Dest": destination to publish the string value
        - "Poll": cannot be < 1

        Raises:
        - NoOptionError - if an expected parameter doesn't exist or if poll is
        < 0.
        """
        super().__init__(publishers, log, params)

        self.num_dest = params("Num-Dest")
        self.str_dest = params("Str-Dest")
        self.start_time = time.time()

        if self.poll < 1:
            raise NoOptionError("Heartbeat poll period is too small!")

        self.log.info("Configuing Heartbeat: msec to {} and str to {} with "
                      "interval {}".format(self.num_dest, self.str_dest,
                                           self.poll))

    def publish_state(self):
        """Calculates the current up time and publishes it as msec and string
        formats.
        """

        uptime = int((time.time() - self.start_time) * 1000)
        self._send(str(uptime), self.num_dest)

        # TODO see if there is some library like timedelta that makes this nicer
        sec = (uptime / (1000)) % 60
        min = (uptime / (1000*60)) % 60
        hr  = (uptime / (1000*60*60)) % 24
        day = int(uptime / (1000*60*60*24))

        msg = ''
        if day > 0:
          msg += '{0}:'.format(day)
        msg += '{0:02d}:{1:02d}:{2:02d}'.format(int(hr), int(min), int(sec))

        self._send(msg, self.num_dest)
