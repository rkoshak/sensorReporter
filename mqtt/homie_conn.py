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


"""Contains the homie connection class.

Classes: HomieConnection
"""
from typing import Callable, Optional, Any, cast
from homie_spec import Node, Property, Device
from homie_spec.properties import Datatype
import paho.mqtt.client as mqtt
from mqtt.mqtt_conn import MqttConnection, REFRESH
from core.utils import ChanType, ChanConst, OUT, IN

OUT_STATE = "state"
IN_CMD_SET = "set"
IN_CMD = "cmd"
PARA_CMD_SRC = "CommandSrc"

class HomieConnection(MqttConnection):
    """ Connects to and enables subscription and publishing to MQTT via Homie convention.

    Developer note: Each sensor and actuator (device) must register its inputs and outputs,
    otherwise it can not be used with the HomieConnection.
    To do so the device calls the "configure_device_channel" function from the core.utils
    once for every output and afterwards the self._register function in the device init().
    Example from the RpiGpioActuator:

    configure_device_channel(self.comm, is_output=False,
                             name="set digital output", datatype=ChanType.ENUM,
                             restrictions="ON,OFF,TOGGLE")
    self._register(self.comm, None)
     """

    def __init__(self,
                 msg_processor:Callable[[str], None],
                 conn_cfg:dict[str, Any]) -> None:
        """ Establishes the MQTT connection and starts the MQTT thread.
            will announce the registered devices to the homie standard
        """
        self.device_id = conn_cfg["DeviceID"].lower()
        self.name = self.device_id + "-sensor_reporter"
        conn_cfg["RootTopic"] = f"homie/{self.device_id}"

        #overwrite conn_cfg["Client"] if not present
        conn_cfg["Client"] = conn_cfg.get("Client", self.device_id)

        #init homie class
        self.device = Device(id=self.device_id, name=self.name, nodes={})

        #override status and refresh topic from parent
        self.lwt = "conn/status"
        self.refresh_comm = { 'Name':'conn',
                             'CommandSrc':f"conn/{REFRESH}/set"
                             }

        super().__init__(msg_processor, conn_cfg)

        #get all topic of this device known by the mqtt server
        self.topics_to_delete:list[str] = []
        device_topic = f"{self.root_topic}/#"
        self.client.subscribe(device_topic, qos=0)
        self.client.message_callback_add(device_topic, self.collect_existing_topics)

        #publish LTW to homie
        self.client.will_set(f"{self.root_topic}/$state", 'lost', qos=2, retain=True)

        #add conneciton properties
        conn_prop = Node(
                name="connection",
                typeOf="conn",
                properties={
                    'status' : Property(name="connection status", datatype=Datatype.STRING,
                                   get=dummy_getter),
                    REFRESH : Property(name="refresh sensor readings", datatype=Datatype.STRING,
                                       settable=True, get=dummy_getter)
                    })
        self.device.nodes["conn"] = conn_prop

    def publish(self,
                message:str,
                comm_conn:dict[str, Any],
                output_name:Optional[str] = None) -> None:
        """ Publishes message to destination, logging if there is an error.

        Arguments:
        - message:     the message to process / publish
        - comm_conn:   dictionary containing only the parameters for the called connection,
                       e. g. information where to publish
        - output_name: optional, the output channel to publish the message to,
                       defines the subdirectory in comm_conn to look for the return topic.
                       When defined the output_name must be present
                       in the sensor YAML configuration:
                       Connections:
                           <connection_name>:
                                <output_name>:
        """
        #if output_name is in the communication dict parse it's contens
        local_comm = comm_conn[output_name] if output_name in comm_conn else comm_conn

        #build destination for homie devices
        #homie expects for recieved commands that the IN_CMD topic is updated
        destination = comm_conn['Name'] + "/" + ( output_name if output_name else IN_CMD )

        retain = True
        if OUT in local_comm.keys():
            retain = local_comm[OUT].get('Retain', True)
        #homie expects topic in lower case
        self._publish_mqtt(message, destination.lower(), retain)

        if output_name is None:
            destination = comm_conn['Name'] + "/" + OUT_STATE
            self._publish_mqtt(message, destination.lower(), retain)

    def register(self,
                 comm_conn:dict[str, Any],
                 handler:Optional[Callable[[str], None]]) -> None:
        """ Registers actuators and sensors with the connection.
            Actuators have to provide a handler to be called on messages received.
            If no handler is provided the registration of a sensor is assumed.

        homie expects following device config:
        Connections:
            homie_conn:
               Name: <homie_device_name>
                $in:
                    Type: <on of [STRING, INTEGER, FLOAT, BOOLEAN, ENUM, COLOR]>
                    FullName: <sting>
                    Unit: <on of [°C", °F, °, L, gal, V, W, A, %, m, ft, Pa, psi, #]>
                    Retain: <True | False>
                    Settable: <True | False>
                $out:
                   Type: <on of [STRING, INTEGER, FLOAT, BOOLEAN, ENUM, COLOR]>
                   FullName: <sting>
                   Unit: <on of [°C", °F, °, L, gal, V, W, A, %, m, ft, Pa, psi, #]>
                   Retain: <True | False>
                   Settable: <True | False>
        """
        n_name = comm_conn['Name']
        #set command source for actuators
        if handler and PARA_CMD_SRC not in comm_conn:
            comm_conn[PARA_CMD_SRC] = f"{n_name}/{IN_CMD}/{IN_CMD_SET}".lower()

        super().register(comm_conn, handler)

        #search for device properties:
        props:dict[str, Property] = {}
        if IN in comm_conn:
            props[IN_CMD] = self.get_property(comm_conn[IN], IN_CMD, n_name)
        if OUT in comm_conn:
            props[OUT_STATE] = self.get_property(comm_conn[OUT], OUT_STATE, n_name)

        if IN not in comm_conn and OUT not in comm_conn:
            for (output, local_comm) in comm_conn.items():
                if isinstance(local_comm, dict):
                    props[output] = self.get_property(local_comm[OUT], output, n_name)

        self.device.nodes[n_name] = Node(name=n_name,
                                        typeOf=comm_conn.get('Type',''),
                                        properties= props)

    @staticmethod
    def get_property(comm_props:dict[str, Any],
                     channel:str,
                     node_name:str) -> Property:
        """ Create homie property from parameters
            Reads the input/output properties from comm_props
            and creates a 'Property' with channel name and device name
            Parameters:
                - comm_props     : the sub-dictionary from connections
                                   created by utils.configure_device_channel
                - channel        : The name of the channel (e. g. Temperature)
                - node_name      : The name of the sensor/actuator
            Returns homie Property containing given settings
        """
        homie_types = {
            ChanType.STRING : Datatype.STRING,
            ChanType.INTEGER : Datatype.INTEGER,
            ChanType.FLOAT : Datatype.FLOAT,
            ChanType.BOOLEAN : Datatype.BOOLEAN,
            ChanType.ENUM : Datatype.ENUM,
            ChanType.COLOR : Datatype.COLOR,
            }
        channel = channel.lower()

        # We know 'comm_props.get(ChanConst.DATATYPE)' will return a ChanType
        # to satisfy the Python type checker we 'cast' the data type
        p_type = homie_types.get(cast(ChanType, comm_props.get(ChanConst.DATATYPE)),
                                 Datatype.STRING)
        p_name = comm_props.get(ChanConst.NAME, channel)
        p_unit = comm_props.get(ChanConst.UNIT)
        p_retained = comm_props.get('Retain')
        p_settable = comm_props.get(ChanConst.SETTABLE)
        p_format = comm_props.get(ChanConst.FORMAT)

        return Property(name=node_name + ' / ' + p_name, datatype=p_type,
                        settable = p_settable, get=dummy_getter,
                        unit = p_unit, retained=p_retained, formatOf=p_format)

    #pylint: disable=unused-argument
    def collect_existing_topics(self,
                                client:mqtt.Client,
                                userdata:Any,
                                msg:mqtt.MQTTMessage) -> None:
        """ read out existing topics for this connection and
            collect them in a list
        """
        if msg.retain and msg.topic not in self.topics_to_delete:
            self.topics_to_delete.append(msg.topic)
            #self.log.debug(f"collected topic: {msg.topic}")
    #pylint: enable=unused-argument

    def publish_device_properties(self) -> None:
        """ Method is intended for connections with auto discover of sensors
            and actuators. Such a connection can place the necessary code for auto
            discover inside this method. It is called after all connections, sensors
            and actuators are created and running.
        """
        state_topic = "$state"
        prop_topic = "$properties"
        #remove and unsubscribe from device messages, was only used to get existing topics
        device_topic = f"{self.root_topic}/#"
        self.client.message_callback_remove(device_topic)
        self.client.unsubscribe(device_topic)

        for msg in self.device.messages():
            #remove used topics from delete list
            if msg.topic in self.topics_to_delete:
                self.topics_to_delete.remove(msg.topic)

            if msg.topic.endswith(prop_topic):
                for prop in msg.payload.split(','):
                    property_path = msg.topic.replace(prop_topic, prop)
                    if property_path in self.topics_to_delete:
                        self.topics_to_delete.remove(property_path)

            #omit $state = ready message so unused topics can get deleted
            if not (msg.topic.endswith(state_topic) and msg.payload == 'ready'):
                #remove root topic since publish_mqtt will add it again
                self._publish_mqtt(msg.payload,
                                   msg.topic.replace(f"{self.root_topic}/",""),
                                   msg.retained)

        for topic in self.topics_to_delete:
            self.log.debug("deleting unused topic: %s", topic)
            #Devices can remove old properties and nodes by
            #publishing a zero-length payload on the respective topics.
            self._publish_mqtt('', topic.replace(f"{self.root_topic}/",""), True)

        self._publish_mqtt('ready', state_topic, True)

        node_keys = ""
        # 'self.device.nodes' could be None
        if isinstance(self.device.nodes, dict):
            node_keys = ", ".join(self.device.nodes.keys())
        self.log.info("Made following devices available for homie auto discover: %s", node_keys)

    def disconnect(self) -> None:
        """ publish homie connection state &
            close the connection to the MQTT broker.
        """
        self._publish_mqtt('disconnected', '$state', True)
        super().disconnect()

def dummy_getter() -> str:
    """ We don't need a getter for some properties,
        but the homie spec expects one in any case.
        So we return an empty string.
    """
    return 'dummy_getter'
