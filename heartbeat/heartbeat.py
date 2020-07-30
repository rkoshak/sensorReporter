import sys
import time
from core.sensor import Sensor
from configparser import NoOptionError

class Heartbeat(Sensor):

    def __init__(self, publishers, log, params):

        super().__init__(publishers, log, params)

        self.num_dest = params("Num-Dest")
        self.str_dest = params("Str-Dest")
        self.start_time = time.time()

        if self.poll == -1:
            raise NoOptionError("Heartbeat requires a non -1 polling period!")

        self.log.info("Configuing Heartbeat: msec to {} and str to {} with "
                      "interval {}".format(self.num_dest, self.str_dest,
                                           self.poll))

    def publish_state(self):

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
