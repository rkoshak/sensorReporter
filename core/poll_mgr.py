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
import time
from multiprocessing import Process

class PollManager:
    """Manages spawing Processes to call a sensor's check method each configured
    polling period. Calling stop will end the polling loop and clean up all the
    resources from the connections, sensors and actuators. When calling report,
    the most recent reading of the sensor is published/republished.
    """

    def __init__(self, connections, sensors, actuators, log):
        """Prepares the manager to start the polling loop. """
        self.log = log
        self.connections = connections
        self.sensors = sensors
        self.actuators = actuators
        self.stop_poll = False
        self.processes = {}

    def __runner(self, target, key):
        """Called in a separate Process, calls the check_state method on a
        sensor and reports if there was an exception raised.

        Arguments:
        - target: the check_state method to call
        - key: helps identify which Sensor entry died
        """
        try:
            target()
        except:
            import traceback
            self.log.error("Error in checking sensor {}: {}"
                           .format(key, traceback.format_exec()))

    def start(self):
        """Kicks off the polling loop. This method will not return until stop()
        is called from a separate thread.
        """
        self.log.info("Starting polling loop")

        while not self.stop_poll:
            for k,s in {k:s for (k,s) in self.sensors.items()
                        if s.poll > 0
                           and (not s.last_poll or
                                (time.time() - s.last_poll) > s.poll)}.items():
                if k in self.processes and self.processes[k].is_alive():
                    self.log.warn("Sensor {} is still running! Skipping poll."
                                  .format(k))
                else:
                    s.last_poll = time.time()
                    proc = Process(target=self.__runner, args=(s.check_state, k))
                    self.processes[k] = proc
                    proc.start()
            # TODO measure the time for the fill loop and warn if it continues
            # to grow.
            time.sleep(0.5)

    def stop(self):
        """Sets a flag to stop the polling loop. Cancels any outstanding
        processes and waits for them to fail, then cleans and disconnects all
        the sensors, actuators, and connections.
        """
        # Stop the polling loop
        self.stop_poll = True
        time.sleep(0.5)

        self.log.info("Cancelling all the polling threads")
        [p.terminate() for p in self.processes.values()]
        [p.join() for p in self.processes.values()]

        self.log.info("Cleaning up the sensors")
        [s.cleanup() for s in self.sensors.values()]

        self.log.info("Cleaning up the actuators")
        [a.cleanup() for a in self.actuators]

        self.log.info("Disconnecting from connections")
        [c.disconnect() for c in self.connections.values()]

    def report(self):
        """Calls publish_state on all the sensors."""
        [s.publish_state() for s in self.sensors]
