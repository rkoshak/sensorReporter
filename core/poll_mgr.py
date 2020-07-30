import time
from multiprocessing import Process

class PollManager:

    def __init__(self, connections, sensors, actuators, log):

        self.log = log
        self.connections = connections
        self.sensors = sensors
        self.actuators = actuators
        self.stop_poll = False
        self.processes = {}

        self.log.info("Initializing SensorReporter")

    def __runner(self, target, key):

        try:
            target()
        except:
            import traceback
            self.log.error("Error in checking sensor {}: {}"
                           .format(key, traceback.format_exec()))

    def start(self):

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
        print("In stop!")

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

        [s.publish_state() for s in self.sensors]
