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

"""This module includes the Actuator parent class.

Classes: Actuator
"""
from abc import ABC, abstractmethod
import logging
from configparser import NoOptionError
from core.utils import set_log_level

class Actuator(ABC):
    """Class from which all actuator capabilities must inherit. Is assumes there
    is a "Topic" param and automatically registers to subscribe to that topic
    with all of the passed in connections. A default implementation is provided
    for all but the on_message method which must be overridden.
    """

    def __init__(self, connections, params):
        """Initializes the Actuator by storing the passed in arguments as data
        members and registers to subscribe to params("Topic").

        Arguments:
        - connections: List of the connections
        - params: lambda that returns value for the passed in key
            "CommandSrc": required, where command to run the actuator come from
            "ResultDest": optional, where the results from the command are
            published.
        Raises:
        - configurationparser.NoOptionError if "CommandSrc" doesn't exist.
        """
        self.log = logging.getLogger(type(self).__name__)
        self.params = params
        self.connections = connections
        self.cmd_src = params("CommandSrc")
        try:
            self.destination = params("ResultsDest")
        except NoOptionError:
            self.destination = None
        set_log_level(params, self.log)

        self._register(self.cmd_src, self.on_message)

    def _register(self, destination, handler):
        """Protected method that registers to the communicator to subscribe to
        destination and process incoming messages with handler.
        """
        for conn in self.connections:
            conn.register(destination, handler)

    @abstractmethod
    def on_message(self, msg):
        """Abstract method that will get called when a message is received on a
        registered destination. Implementers should execute the action the
        Actuator performes.
        """

    def cleanup(self):
        """Called to give the Actuator a chance to close down and release any
        resources.
        """

    def _publish(self, message, destination, filter_echo=False):
        """Protected method that will publish the passed in message to the
        passed in destination to all the passed in connections.

        Parameter filter_echo is intended to activate a filter for looped back messages
        """
        for conn in self.connections:
            conn.publish(message, destination, filter_echo)

    def publish_actuator_state(self):
        """Called to publish the current state of the actuator to the publishers.
        The default implementation is a pass.
        """