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
from configparser import NoOptionError
from core.utils import set_log_level

class Connection(ABC):
    """Parent class that all connections must implement. It provides a default
    implementation for all methods except publish which must be overridden.
    """

    def __init__(self, msg_processor, params):
        """Stores the passed in arguments as data members.

        Arguments:
        - msg_processor: Connections will subscribe to a destination for
        communication to the program overall, not an individual actuator or
        sensor. This is the method that gets called when a message is received.
        - params: set of properties from the loaded ini file.
        """
        self.log = logging.getLogger(type(self).__name__)
        self.msg_processor = msg_processor
        self.params = params
        set_log_level(params, self.log)

    @abstractmethod
    def publish(self, message, destination):
        """Abstarct method that must be overriden. When called, send the passed
        in message to the passed in destination.
        """

    def disconnect(self):
        """Disconnect from the connection and release any resources."""

    def register(self, destination, handler):
        """Set up the passed in handler to be called for any message on the
        destination.
        """

class LocalConnection(Connection):
    """A special connection that can link Sensors and Actuators to other
    Actuators. One of three optional parameters can be provided:
    "OnEq": if message equal to this parameter is received publish "ON", works
    with String messages
    "OnGT": if the message is greater than this value, publsih "ON", only works
    with messages that can be parsed to float.
    "OnLT": if the message is less than this value, publish "ON", only works
    with messages that can be parsed to float.

    If none of the optional parameters are present, the message is passes as is.
    All messages that don't match the comparison results in "OFF". If more than
    one is defined, OnEQ is first and OnGT is second and OnLT is last.

    This can be used to, for example, turn on an LED attached to a GPIO pin
    configured with RpiGpioActuator when a sensor has a given value.
    """

    def __init__(self, msg_processor, params):
        super().__init__(msg_processor, params)

        self.registered = {}
        self.eq = None
        self.gt = None
        self.lt = None

        try:
            self.eq = params("OnEq")
        except NoOptionError:
            pass
        try:
            if not self.eq:
                self.gt = float(params("OnGT"))
        except NoOptionError:
            pass
        try:
            if not self.eq and not self.gt:
                self.lt = float(params("OnLT"))
        except NoOptionError:
            pass

    def publish(self, message, destination):
        """Send the message or, if defined, translate the message to ON or OFF."""
        if destination in self.registered:
            try:
                send = message
                if self.eq and message == self.eq:
                    send = "ON"
                elif self.eq:
                    send = "OFF"
                elif self.gt and float(message) > self.gt:
                    send = "ON"
                elif self.gt:
                    send = "OFF"
                elif self.lt and float(message) < self.lt:
                    send = "ON"
                elif self.lt:
                    send = "OFF"
                self.log.info("Received message %s, forwarding %s to %s", message,
                              send, destination)
                self.registered[destination](send)
            except ValueError:
                self.log.error("'%s' cannot be parsed to float!", message)
        else:
            self.log.error("There is no handler registered for %s", destination)

    def register(self, destination, handler):
        self.log.info("Registering destination %s", destination)
        self.registered[destination] = handler
