from abc import ABC, abstractmethod
class Connection(ABC):

    def __init__(self, msg_processor, log, params):

        self.log = log
        self.msg_processor = msg_processor
        self.params = params

    @abstractmethod
    def publish(self, message, destination):
        pass

    def disconnect(self):
        pass

    def register(self, topic, handler):
        pass
