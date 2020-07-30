from abc import ABC
from configparser import NoOptionError

class Sensor(ABC):

    def __init__(self, publishers, log, params):

        self.publishers = publishers
        self.log = log
        self.params = params
        try:
            self.poll = int(params("Poll"))
        except NoOptionError:
            self.poll = -1
        self.last_poll = None

    def check_state(self):

        self.publish_state()

    def publish_state(self):

        pass

    def _send(self, msg, dest):

        [conn.publish(msg, dest) for conn in self.publishers]

    def cleanup(self):

        pass
