from abc import ABC, abstractmethod

class Actuator(ABC):

    def __init__(self, connections, log, params):

        self.log = log
        self.params = params
        self.connections = connections
        self.destination = params("Topic")

        self._register(self.destination, self.on_message)

    def _register(self, destination, handler):

        [conn.register(destination, handler) for conn in self.connections]

    @abstractmethod
    def on_message(self, client, userdata, msg):

        pass

    def cleanup(self):

        pass

    def _publish(self, message, topic):

        [conn.publish(message, topic) for conn in self.connections]
