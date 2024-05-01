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
from typing import Any, Callable, Optional, Dict, TYPE_CHECKING
import logging
from core import utils
if TYPE_CHECKING:
    # Fix circular imports needed for the type checker
    from core import connection

class Actuator(ABC):
    """ Class from which all actuator capabilities must inherit. It assumes there
        is a "Topic" param and automatically registers to subscribe to that topic
        with all of the passed in connections. A default implementation is provided
        for all but the on_message method which must be overridden.
    """

    def __init__(self,
                 connections:Dict[str, 'connection.Connection'],
                 dev_cfg:Dict[str, Any]) -> None:
        """ Initializes the Actuator by storing the passed in arguments as data
            members and registers to subscribe to params("Topic").

        Arguments:
        - connections: Dictionary of connection-instances,
                       not to be confused with the 'Connections:' section within the actuator config
        - dev_cfg:  Dictionary that holds the device specific config
                    "Connections": required, holds the dictionaries with the configured connections
                    will subscribe to the topic and report the status
                    to the return topic if it is specified
        Raises:
        - KeyError if "Connections" doesn't exist.

        Important Parameters:
        - self.comm: communication dictionary, with information where to publish
                     contains connection named dictionaries for each connection
        - self.log: The log instance for this device
        - self.name: device name, useful for log entries
        """
        self.log = logging.getLogger(type(self).__name__)
        self.dev_cfg = dev_cfg
        self.connections = connections
        self.comm:Dict[str, Any] = dev_cfg['Connections']
        # Actuator Name is specified in sensor_reporter.py > creat_device()
        # dev_cfg.get('Name') should be already a string, to make it clear for mypy use str()
        self.name = str(dev_cfg.get('Name'))
        utils.set_log_level(dev_cfg, self.log)

        self._register(self.comm, self.on_message)

        # Verify that utils.CONF_ON_DISCONNECT & utils.CONF_ON_RECONNECT
        # in 'Connections:' contain valid values!
        # Actuators have no output channel => None
        utils.verify_connections_layout(self.comm, self.log, self.name, None)

    def _register(self,
                  comm:Dict[str, Any],
                  handler:Optional[Callable[[str], None]]) -> None:
        """ Protected method that registers to the communicator to subscribe to
            destination and process incoming messages with handler.
        """

        for (conn, comm_conn) in comm.items():
            self.connections[conn].prepare_register(comm_conn, handler)

    @abstractmethod
    def on_message(self,
                   msg:str) -> None:
        """ Abstract method that will get called when a message is received on a
            registered destination. Implementers should execute the action the
            Actuator performs.

            Argument 'msg' is the string message which was received from a connection
                     to trigger a actuator specific action
        """

    def cleanup(self) -> None:
        """ Called to give the Actuator a chance to close down and release any
            resources.
        """

    def _publish(self,
                 message:str,
                 comm:Dict[str, Any]) -> None:
        """ Protected method that will publish the passed in message to the
            passed in comm(unicators).

        Arguments:
        - message:     the message to publish
        - comm:        communication dictionary, with information where to publish
                       contains connection named dictionaries for each connection,
                       containing the connection related parameters
        """
        for conn in comm.keys():
            # currently for actuators the connectors don't support the parameter output_name
            # so we set it to None
            self.connections[conn].prepare_publish(message, comm[conn], None)

    def publish_actuator_state(self) -> None:
        """ Called to publish the current state of the actuator to the publishers.
            The default implementation is a pass.
        """
