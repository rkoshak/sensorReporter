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
""" A special connection to have a sensor activate an actuator that is part of
    this instance of sensor_reporter.

Classes:
    - LocalConnection: allows sensors to call local actuators.
"""
from typing import Callable, Optional, Any, Dict
from core.connection import Connection
from core.utils import is_toggle_cmd

class LocalConnection(Connection):
    """ A special connection that can link Sensors and Actuators to other
        Actuators. One of three optional parameters can be provided:
        "OnEq": if message equal to this parameter is received publish "ON", works
                with String messages
        "OnGT": if the message is greater than this value, publish "ON", only works
                with messages that can be parsed to float.
        "OnLT": if the message is less than this value, publish "ON", only works
                with messages that can be parsed to float.

    If none of the optional parameters are present, the message is passes as is.
    All messages that don't match the comparison results in "OFF". If more than
    one is defined, OnEQ is first and OnGT is second and OnLT is last.

    This can be used to, for example, turn on an LED attached to a GPIO pin
    configured with RpiGpioActuator when a sensor has a given value.
    Configure this as a connection and configure both the sensor and the
    actuator to use this Connection.
    """

    def __init__(self,
                 msg_processor:Callable[[str], None],
                 conn_cfg:Dict[str, Any]) -> None:
        """ Initializes a local connection. Supports a few simple comparisons
            which can cause the incoming message to be translated to ON/OFF.

        conn_cfg:
            - "OnEq": any message that matches will be converted to "ON" and all
            other messages will result in "OFF".
            - "OnGT": assumes the message is a number, if the incoming message
            is greater than the parameter value "ON" is published; in all other
            cases "OFF" is published.
            - "OnLT": assumes the message is a number, if the incoming message
            is less than the parameter value "ON" is published; in all other
            cases "OFF" is published.

        If more than one of the above is present, the first one found in the
        order listed above will be used and the others ignored.

        If none of the above parameters are defined, the message is published
        unmodified.

        The mqg_processor parameter is ignored, this connection cannot cause
        sensor_reporter to republish the sensor values.
        """
        super().__init__(msg_processor, conn_cfg)

        self.gt = None
        self.lt = None

        self.eq = conn_cfg.get("OnEq")
        try:
            if not self.eq:
                self.gt = float(conn_cfg["OnGT"])
        except KeyError:
            pass
        try:
            if not self.eq and not self.gt:
                self.lt = float(conn_cfg["OnLT"])
        except KeyError:
            pass

    def publish(self,
                message:str,
                comm_conn:Dict[str, Any],
                output_name:Optional[str] = None) -> None:
        """ Send the message or, if defined, translate the message to ON or OFF.

        Arguments:
        - message:     the message to process / publish
        - comm_conn:   dictionary containing only the parameters for the called connection,
                       e. g. information where to publish
        - output_name: optional, the output channel to publish the message to,
                       defines the sub-directory in comm_conn to look for the return topic.
                       When defined the output_name must be present
                       in the sensor YAML configuration:
                       Connections:
                           <connection_name>:
                                <output_name>:
        """
        #if output_name is in the communication dict parse it's contents
        local_comm = comm_conn[output_name] if output_name in comm_conn else comm_conn

        destination = local_comm.get('StateDest')
        if destination in self.registered:
            try:
                send = message
                # forward TOGGLE and ISO formated time messages
                if is_toggle_cmd(message):
                    send = "TOGGLE"
                elif self.eq and message == self.eq:
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
        elif destination is None:
            #make 'StatusDest' optional
            return
        else:
            self.log.debug("There is no handler registered for %s", destination)

    def register(self,
                 comm_conn:Dict[str, Any],
                 handler:Optional[Callable[[str], None]]) -> None:
        """ Set up the passed in handler to be called for any message on the
            destination.

        Arguments:
            - comm_conn: the dictionary containing the connection related parameters
            - handler:   (reference to function) handles the incoming commands,
                         if None the registration of a sensor is assumed
        """
        if handler:
            self.log.info("Registering destination %s", comm_conn['CommandSrc'])
            self.registered[comm_conn['CommandSrc']] = handler
