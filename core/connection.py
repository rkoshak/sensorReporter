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
from abc import ABC, abstractmethod

class Connection(ABC):
    """Parent class that all connections must implement. It provides a default
    implementation for all methods except publish which must be overridden.
    """

    def __init__(self, msg_processor, log, params):
        """Stores the passed in arguments as data members.

        Arguments:
        - msg_processor: Connections will subscribe to a destination for
        communication to the program overall, not an individual actuator or
        sensor. This is the method that gets called when a message is received.
        - log: used for logging out important information.
        - params: set of properties from the loaded ini file.
        """
        self.log = log
        self.msg_processor = msg_processor
        self.params = params

    @abstractmethod
    def publish(self, message, destination):
        """Abstarct method that must be overriden. When called, send the passed
        in message to the passed in destination.
        """
        pass

    def disconnect(self):
        """Disconnect from the connection and release any resources."""
        pass

    def register(self, destination, handler):
        """Set up the passed in handler to be called for any message on the
        destination.
        """
        pass
