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
from core.utils import set_log_level

class Actuator(ABC):
    """Class from which all actuator capabilities must inherit. Is assumes there
    is a "Topic" param and automatically registers to subscribe to that topic
    with all of the passed in connections. A default implementation is provided
    for all but the on_message method which must be overridden.
    """

    def __init__(self, connections, dev_cfg):
        """Initializes the Actuator by storing the passed in arguments as data
        members and registers to subscribe to params("Topic").

        Arguments:
        - connections: List of the connections
        - dev_cfg: dictionary that holds the device specific config
            "Connections": required, holds the dictionarys with the configured connections
            will subscribe to the topic and report the status
            to the return topic if it is specified
        Raises:
        - KeyError if "Connections" doesn't exist.
        """
        self.log = logging.getLogger(type(self).__name__)
        self.dev_cfg = dev_cfg
        self.connections = connections
        self.comm = dev_cfg['Connections']
        #Actuator Name is specified in sensor_reporter.py > creat_device()
        self.name = dev_cfg.get('Name')
        set_log_level(dev_cfg, self.log)

        self._register(self.comm, self.on_message)

    def _register(self, comm, handler):
        """Protected method that registers to the communicator to subscribe to
        destination and process incoming messages with handler.
        """

        for (conn, values) in comm.items():
            self.connections[conn].register(values, handler)

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

    def _publish(self, message, comm):
        """Protected method that will publish the passed in message to the
        passed in destination to all the passed in connections.
        """
        for conn in comm.keys():
            self.connections[conn].publish(message, comm[conn])

    def publish_actuator_state(self):
        """Called to publish the current state of the actuator to the publishers.
        The default implementation is a pass.
        """
