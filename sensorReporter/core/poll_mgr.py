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

"""Contains the PollManager class, the class that drives the sensor_reporter.

Classes: PollManager
"""
import time
from threading import Thread
import traceback
import logging

class PollManager:
    """Manages spawing Processes to call a sensor's check method each configured
    polling period. Calling stop will end the polling loop and clean up all the
    resources from the connections, sensors and actuators. When calling report,
    the most recent reading of the sensor is published/republished.
    """

    def __init__(self, connections, sensors, actuators):
        """Prepares the manager to start the polling loop. """
        self.log = logging.getLogger(type(self).__name__)
        self.connections = connections
        self.sensors = sensors
        self.actuators = actuators
        self.stop_poll = False
        self.threads = {}

    def start(self):
        """Kicks off the polling loop. This method will not return until stop()
        is called from a separate thread.
        """
        self.log.info("Starting polling loop")

        while not self.stop_poll:
            for key, sen in {key:sen for (key, sen) in self.sensors.items()
                             if sen.poll > 0
                             and (not sen.last_poll or
                                  (time.time() - sen.last_poll) > sen.poll)}.items():
                if key in self.threads and self.threads[key].is_alive():
                    self.log.warning("Sensor %s is still running! Skipping poll.",
                                     key)
                else:
                    # Wrap the call so we can catch and report exceptions.
                    def runner(target, key):
                        try:
                            target()
                        # TODO create a special exception to catch
                        except:
                            self.log.error("Error in checking sensor %s: %s", key,
                                           traceback.format_exc())

                    sen.last_poll = time.time()
                    thread = Thread(target=runner,
                                    args=(sen.check_state, key))
                    self.threads[key] = thread
                    thread.start()
            # TODO measure the time for the fill loop and warn if it continues
            # to grow.
            time.sleep(0.5)

    def stop(self):
        """Sets a flag to stop the polling loop. Cancels any outstanding
        processes and waits for them to fail, then cleans and disconnects all
        the sensors, actuators, and connections.
        """
        # Stop the polling loop
        # TODO add an Event object that we can use to interrupt sleeps in sensors
        self.stop_poll = True
        time.sleep(0.5)

        self.log.info("Waiting for all the polling threads")
        for thread in self.threads.values():
            thread.join()

        self.log.info("Cleaning up the sensors")
        for sen in self.sensors.values():
            sen.cleanup()

        self.log.info("Cleaning up the actuators")
        for act in self.actuators:
            act.cleanup()

        self.log.info("Disconnecting from connections")
        for conn in self.connections.values():
            conn.disconnect()

    def report(self):
        """Calls publish_state on all the sensors and actuators."""
        for sen in self.sensors.values():
            sen.publish_state()

        for act in self.actuators:
            act.publish_actuator_state()
