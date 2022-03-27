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

"""Contains the parent Connection class.

Classes: Connections
"""
from abc import ABC, abstractmethod
import logging
from core.utils import set_log_level

class Connection(ABC):
    """Parent class that all connections must implement. It provides a default
    implementation for all methods except publish which must be overridden.
    """

    def __init__(self, msg_processor, conn_cfg):
        """Stores the passed in arguments as data members.

        Arguments:
        - msg_processor: Connections will subscribe to a destination for
        communication to the program overall, not an individual actuator or
        sensor. This is the method that gets called when a message is received.
        - conn_cfg: set of properties from the loaded yaml file.
        """
        self.log = logging.getLogger(type(self).__name__)
        self.msg_processor = msg_processor
        self.conn_cfg = conn_cfg
        self.registered = {}
        set_log_level(conn_cfg, self.log)

    @abstractmethod
    def publish(self, message, comm):
        """Abstarct method that must be overriden. When called, send the passed
        in message to the passed in destination.
        """

    def disconnect(self):
        """Disconnect from the connection and release any resources."""

    def register(self, comm, handler):
        """Set up the passed in handler to be called for any message on the
        destination. Default implementation assumes topic 'CommandSrc'
        """
        self.log.info("Registering destination %s", comm['CommandSrc'])
        self.registered[comm['CommandSrc']] = handler
