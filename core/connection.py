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
from enum import Enum, auto
from typing import Union, Callable, Optional
import logging
# workaround circular import connection <=> utils, import only file but not the method/object
from core import utils

# connection sub directory constants
CONF_COMM_CONN = 'comm_conn'
CONF_HANDLER = 'Handler'

VAL_SEND_READINGS = 'SendReadings'
VAL_NO_OF_READINGS = 'NumberOfReadings'
VAL_CHANGE_STATE = 'ChangeState'
VAL_TARGET_STATE = 'TargetState'
VAL_TIMEOUT = 'Timeout'
VAL_RESUME_STATE = 'ResumeLastState'
VAL_LAST_STATE = 'LastState'

class ConnState(Enum):
    """ connection state constants """
    INIT = auto()
    OFFLINE = auto()
    PRE_OFFLINE = auto()
    CONNECTING = auto()
    PRE_ONLINE = auto()
    ONLINE = auto()

class Connection(ABC):
    """ Parent class that all connections must implement. It provides a default
        implementation for all methods except publish which must be overridden.
    """

    def __init__(self, msg_processor, conn_cfg):
        """ Stores the passed in arguments as data members.

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
        self.state = ConnState.INIT
        self.value_send_buff = {}
        self.online_offline_act = {}
        utils.set_log_level(conn_cfg, self.log)

    @abstractmethod
    def publish(self, message, comm_conn, output_name=None):
        """ Abstract method that must be overridden. When called, send the passed
            in message to the passed in comm(unication)_conn(ection) related dictionary.
            An output_name can be specified optional to set a output channel to publish to.

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

    def prepare_publish(self,
                        message:Union[str, dict],
                        comm_conn:dict,
                        output_name:Optional[str]=None) -> None:
        """ Internal method to store messages in case the connection is offline.
            If a sensor doesn't has 'ConnectionOnReconnect' configured, send messages
            get dropped while the connection is offline.

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
        ### Store sensor messages if offline ###
        # Create ID for communication dictionary to find same sensor/actuator later on
        comm_id = id(comm_conn)
        if self.state == ConnState.OFFLINE:
            # Check if caller has 'ConnectionOnReconnect' configured
            if utils.CONF_ON_RECONNECT in comm_conn and \
            isinstance(comm_conn[utils.CONF_ON_RECONNECT], dict):
                # Read 'ConnectionOnReconnect' properties
                pub_values_on_reconnect = comm_conn[utils.CONF_ON_RECONNECT \
                                                    ].get(VAL_SEND_READINGS, False)
                number_readings_to_send = comm_conn[utils.CONF_ON_RECONNECT \
                                                    ].get(VAL_NO_OF_READINGS, 1)
                if pub_values_on_reconnect:
                    # Create new entry in send_buff dict if comm_conn ID not present
                    if comm_id not in self.value_send_buff:
                        self.value_send_buff[comm_id] = { CONF_COMM_CONN : comm_conn }
                    # Create empty array if output_name is not in send_buff
                    if output_name not in self.value_send_buff[comm_id]:
                        self.value_send_buff[comm_id][output_name] = []
                    # Remove first stored message if No. of readings length reached
                    if len(self.value_send_buff[comm_id][output_name]) >= number_readings_to_send:
                        self.value_send_buff[comm_id][output_name].pop(0)
                    # Store sensor reading, with ID of comm_conn
                    self.value_send_buff[comm_id][output_name].append(message)
                    self.log.debug("OFFLINE: Appended msg '%s' for output '%s' "
                                   "to send buffer ID %i",
                                   message, output_name, comm_id)
                    # self_value_send_buff structure:
                    # <ID of sensor/actuator's comm_conn>:
                    #     conn_comm:
                    #         <published communication dictionary>
                    #     <output_name1>: [ <array of resent sensor readings> ]
                    #     <output_name2>: [ <array of resent sensor readings> ]
        if self.state in [ConnState.OFFLINE, ConnState.PRE_ONLINE, ConnState.PRE_OFFLINE]:
            # Only publish messages when ONLINE or in INIT state
            return

        ### Store message from actuators as last state while ONLINE or in INIT state ###
        # Check if comm_id is in online_act dict, if so store current actuator state
        if comm_id in self.online_offline_act and \
        utils.CONF_ON_RECONNECT in self.online_offline_act[comm_id]:
            # Currently output_name is only supported for sensors,
            # so we only need to store the message.
            self.online_offline_act[comm_id][utils.CONF_ON_RECONNECT][VAL_LAST_STATE] = message
            self.log.debug("RECONNECT: stored state %s for actuator ID %i",
                           message, comm_id)

        self.publish(message, comm_conn, output_name)

    def publish_device_properties(self):
        """ Method is intended for connections with auto discover of sensors
            and actuators. Such a connection can place the necessary code for auto
            discover inside this method. It is called after all connections, sensors
            and actuators are created and running.

        Since not all connections support auto discover the default implementation is empty.
        """

    def disconnect(self):
        """ Disconnect from the connection and release any resources.
            Override this method to implement a connection related disconnect procedure.
        """

    def prepare_disconnect(self) -> None:
        """ Internal method to disable offline action before intentional disconnect request.
            Offline actions won't get trigger if self.state is already offline.
        """
        self.state = ConnState.OFFLINE
        self.disconnect()

    @abstractmethod
    def register(self, comm_conn, handler):
        """ Set up the passed in handler to be called for any message on the
            destination.

            handler is a function with one string parameter
            containing the received command:

            def on_message(msg):

        Arguments:
            - comm_conn: the dictionary containing the connection related parameters
            - handler:   (reference to function) handles the incoming commands,
                         if None the registration of a sensor is assumed
        """

        # Example implementation to register topic 'CommandSrc' with handler
        # if handler:
        #    self.log.info("Registering destination %s", comm_conn['CommandSrc'])
        #    self.registered[comm_conn['CommandSrc']] = handler

    def prepare_register(self,
                         comm_conn:dict,
                         handler:Callable[[str], None]) -> None:
        """ Internal method to register connection related actuator actions
            which get triggered when the connection calls conn_went_offline() or
            conn_went_online()

        Arguments:
            - comm_conn: the dictionary containing the connection related parameters
            - handler:   (reference to function) handles the incoming commands,
                         if None the registration of a sensor is assumed.
                         Handler must accept one string input parameter.
        """
        # Only process actuators
        if handler is not None:
            # init variables
            on_reconnect = on_disconnect = None

            # self.online_offline_act structure:
            # <ID of actuator's comm_conn>:
            #     handler : < reference to handler which handles received messages >
            #     ConnectionOnDisconnect:
            #            ChangeState: < yes/no >
            #            TargetState: < string >
            #     ConnectionOnReconnect:
            #            ResumeLastState: < yes/no >
            #            ChangeState: < yes/no >
            #            TargetState: < string >

            # check if online/offline actions are configured, grab config if found
            if utils.CONF_ON_RECONNECT in comm_conn and \
            isinstance(comm_conn[utils.CONF_ON_RECONNECT], dict):
                on_reconnect = comm_conn[utils.CONF_ON_RECONNECT]
            if utils.CONF_ON_DISCONNECT in comm_conn and \
            isinstance(comm_conn[utils.CONF_ON_DISCONNECT], dict):
                on_disconnect = comm_conn[utils.CONF_ON_DISCONNECT]
            # create sub-directory if entry was found
            if on_reconnect or on_disconnect:
                comm_id = id(comm_conn)
                self.online_offline_act[comm_id] = {CONF_HANDLER : handler}
                if on_reconnect:
                    self.online_offline_act[comm_id][utils.CONF_ON_RECONNECT] = on_reconnect
                if on_disconnect:
                    self.online_offline_act[comm_id][utils.CONF_ON_DISCONNECT] = on_disconnect
                #self.log.debug("Registered onl/offl action %s", self.online_offline_act[comm_id])

        self.register(comm_conn, handler)

    def conn_went_offline(self):
        """ The inheriting class may call this function to trigger related actions
            when the connection goes offline.

            e.g. set configured actuator state from section 'ConnectionOnDisconnect'
        """
        # Check current state, don't proceed if already offline
        if self.state == ConnState.OFFLINE:
            return

        self.state = ConnState.PRE_OFFLINE
        self.log.debug("Disconnect action: applying configured actuator states")

        # self.online_offline_act structure:
        # <ID of actuator's comm_conn>:
        #     handler : < reference to handler which handles received messages >
        #     ConnectionOnDisconnect:
        #            ChangeState: < yes/no >
        #            TargetState: < string >
        #     ConnectionOnReconnect:
        #            ResumeLastState: < yes/no >
        #            ChangeState: < yes/no >
        #            TargetState: < string >

        # Trigger action on registered actuators
        for entry in self.online_offline_act.values():
            handler = entry[CONF_HANDLER]
            on_disconnect = entry.get(utils.CONF_ON_DISCONNECT, {})
            # check if state should change
            if on_disconnect.get(VAL_CHANGE_STATE, False):
                target_state = on_disconnect.get(VAL_TARGET_STATE, None)
                if target_state is not None:
                    # send target state to handler as string
                    #self.log.debug("Offline action: send target state %s", target_state)
                    handler(str(target_state))

        self.state = ConnState.OFFLINE

    def conn_is_connecting(self):
        """ The inheriting class may call this function to tell the base class,
            that the connection is available again. So massages send during
            connecting won't get stored in the self.value_send_buff
        """
        # ignore first time the connector is connecting
        if self.state == ConnState.INIT:
            return
        self.state = ConnState.CONNECTING

    def conn_went_online(self):
        """ The inheriting class may call this function to tell the base class,
            that the connection is online again.

            The first time a connection goes online nothing happens.

            Stored sensor readings will be published and configured actuator
            actions will be set.
            e.g.set configured actuator state from section 'ConnectionOnDisconnect'
                or publish configured sensor readings on connection reconnect
        """
        last_state = self.state
        self.state = ConnState.PRE_ONLINE

        if last_state in [ConnState.OFFLINE, ConnState.CONNECTING]:
            self.log.debug("Reconnect action: applying configured actuator states")

            # self.online_offline_act structure:
            # <ID of actuator's comm_conn>:
            #     handler : < reference to handler which handles received messages >
            #     ConnectionOnDisconnect:
            #            ChangeState: < yes/no >
            #            TargetState: < string >
            #     ConnectionOnReconnect:
            #            ResumeLastState: < yes/no >
            #            ChangeState: < yes/no >
            #            TargetState: < string >

            # Trigger action on registered actuators
            for entry in self.online_offline_act.values():
                handler = entry[CONF_HANDLER]
                on_reconnect = entry.get(utils.CONF_ON_RECONNECT, {})
                # check if state should change
                target_state = None
                if on_reconnect.get(VAL_CHANGE_STATE, False):
                    target_state = on_reconnect.get(VAL_TARGET_STATE, None)
                elif on_reconnect.get(VAL_RESUME_STATE, False):
                    target_state = on_reconnect.get(VAL_LAST_STATE, None)
                if target_state is not None:
                    # send target state to handler as string
                    handler(str(target_state))

        self.state = ConnState.ONLINE
        if last_state in [ConnState.INIT, ConnState.ONLINE]:
            # don't run on initial connect or when set online state twice
            return

        ###          Send stored sensor readings                 ###
        self.log.debug("Reconnect action: sending stored sensor readings")
        # self_value_send_buff structure:
        # <ID of sensor/actuator's comm_conn>:
        #     conn_comm:
        #         <published communication dictionary>
        #     <output_name1>: [ <array of resent sensor readings> ]
        #     <output_name2>: [ <array of resent sensor readings> ]
        for entry in self.value_send_buff.values():
            comm_conn = entry.pop(CONF_COMM_CONN)
            # after popping CONF_COMM_CONN the dict only contains output_names with readings
            for (output_name, messages) in entry.items():
                for msg in messages:
                    self.publish(msg, comm_conn, output_name)
        # empty send buffer, since all messages got sent
        self.value_send_buff.clear()
