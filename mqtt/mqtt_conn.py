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

"""Contains the MQTT connection class.

Classes: MqttConnection
"""
import socket
import traceback
from time import sleep
from typing import Callable, Optional, Any, Tuple, Dict
import paho.mqtt.client as mqtt
from core.connection import Connection

REFRESH = "refresh"
ONLINE = "ONLINE"
OFFLINE = "OFFLINE"

class MqttConnection(Connection):
    """ Connects to and enables subscription and publishing to MQTT."""

    def __init__(self,
                 msg_processor:Callable[[str], None],
                 conn_cfg:Dict[str, Any]) -> None:
        """ Establishes the MQTT connection and starts the MQTT thread.
            Expects the following parameters in params:
            - "Host": hostname or IP address of the MQTT broker
            - "Port": port for the MQTT broker
            - "Client": client ID to register with the MQTT broker, must be unique
            - "RootTopic": root topic that will be the vase of the topic hierarchy
                        this connection subscribes and publishes to.
            - "TLS": optional parameters to determine if the connection should be
                    encrypted using TLS.
            - "CAcert": Optional path to the CA cert file.
                        If not set, default is ./certs/ca.crt
            - "TLSinsecure": Optional parameter to disable check of hostname in the
                            certificate. Default is False.
            - "User": MQTT broker login user name
            - "Password": MQTT broker login password
            - "Keepalive": MQTT keepalive parameter

        If the connection fails, it will keep retrying every five seconds until
        the connection is successful.

        RootTopic/status is the LWT topic and will have ONLINE/OFFLINE published
        as a retained message to indicate the online status of this connection.
        RootTopic/refresh is the topic listened to so external clients can send
        messages to sensor_reporter
        """
        super().__init__(msg_processor, conn_cfg)
        self.log.info("Initializing MQTT Connection...")
        #define lwt and refresh_comm if not defined from child class
        if not hasattr(self, 'lwt') and not hasattr(self, 'refresh_comm'):
            self.lwt = "status"
            self.refresh_comm = { 'CommandSrc':REFRESH }

        # Get the parameters, raises KeyError if one doesn't exist
        self.host = conn_cfg["Host"]
        self.port = int(conn_cfg["Port"])
        client_name = conn_cfg["Client"]
        self.root_topic = conn_cfg["RootTopic"]

        #optional parameters
        tls = conn_cfg.get("TLS", False)
        ca_cert = conn_cfg.get("CAcert", None)
        tls_insecure = conn_cfg.get("TLSinsecure", False)

        user = conn_cfg["User"]
        passwd = conn_cfg["Password"]
        self.keepalive = int(conn_cfg["Keepalive"])

        self.msg_processor = msg_processor

        # Initialize the client
        self.client = mqtt.Client(client_id=client_name, clean_session=True)
        if tls:
            self.log.debug("TLS is true, CA cert is: {}".format(ca_cert))
            if ca_cert:
                self.client.tls_set(ca_cert)
            else:
                self.client.tls_set()
            self.log.debug("TLS insecure is {}".format(tls_insecure))
            self.client.tls_insecure_set(tls_insecure)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_publish = self.on_publish
        self.client.username_pw_set(user, passwd)

        self.log.info(
            "Attempting to connect to MQTT broker at %s:%s", self.host, self.port
        )
        self.connected = False
        self._connect()

        lwtt = "{}/{}".format(self.root_topic, self.lwt)
        ref = "{}/{}".format(self.root_topic, REFRESH)

        self.log.info(
            "LWT topic is %s, subscribing to refresh topic %s", lwtt, ref)
        self.client.will_set(lwtt, OFFLINE, qos=2, retain=True)
        self.register(self.refresh_comm, msg_processor)

        self.client.loop_start()

        # ONLINE state for lwtt and the base class will be set
        # after fully connected in on_connect()

    def _connect(self) -> None:
        while not self.connected:
            try:
                self.client.connect(self.host, port=self.port,
                                    keepalive=self.keepalive)
                self.connected = True
            except socket.error:
                self.log.error("Error connecting to %s:%s",
                               self.host, self.port)
                self.log.debug("Exception: %s", traceback.format_exc())
                sleep(5)
                self.connected = False

        self.log.info("Connection to MQTT is successful")
        super().conn_is_connecting()

    def publish(self,
                message:str,
                comm_conn:Dict[str, Any],
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
        #if output_name is in the communication dict parse it's contents
        local_comm = comm_conn[output_name] if output_name in comm_conn else comm_conn

        destination = local_comm.get('StateDest')
        retain = local_comm.get('Retain', False)

        #if output_name (output) is not present in comm_conn, StateDest will be None
        if destination is None:
            return

        self._publish_mqtt(message, destination, retain)

    def _publish_mqtt(self,
                      message:str,
                      topic:str,
                      retain:bool) -> None:
        try:
            if not self.connected:
                self.log.warning(
                    "MQTT is not currently connected!"
                    " Ignoring message: %s, for topic: %s" , message, topic)
                return
            full_topic = "{}/{}".format(self.root_topic, topic)
            rval = self.client.publish(
                        full_topic, message, retain=retain, qos=0)
            if rval[0] == mqtt.MQTT_ERR_NO_CONN:
                self.log.error(
                    "Error puiblishing update %s to %s", message, full_topic)
            else:
                self.log.debug(
                    "Published message %s to %s retain=%s", message, full_topic, retain
                )
        except ValueError:
            self.log.error(
                "Unexpected error publishing MQTT message: %s", traceback.format_exc()
            )

    def disconnect(self) -> None:
        """ Closes the connection to the MQTT broker."""
        self.log.info("Disconnecting from MQTT")
        self._publish_mqtt(OFFLINE, self.lwt, True)
        self.client.loop_stop()
        self.client.disconnect()

    def register(self,
                 comm_conn:Dict[str, Any],
                 handler:Optional[Callable[[str], None]]) -> None:
        """ Registers a handler to be called on messages received on topic
            appended to the root_topic. Handler is expected to take one argument,
            the message.
        """
        #handler can be None if a sensor registers it's outputs
        if handler:
            destination = comm_conn['CommandSrc']
            full_topic = "{}/{}".format(self.root_topic, destination)
            self.log.info("Registering for messages on '%s'", full_topic)

            def on_message(client:mqtt.Client,
                           userdata:Any,
                           msg:mqtt.MQTTMessage) -> None:
                message = msg.payload.decode("utf-8")

                self.log.debug(
                    "Received message client %s userdata %s and msg %s",
                    client,
                    userdata,
                    message,
                )
                handler(message)

            # We use self.registered here only to store the topic to re-subscribe later.
            # The handler in .register is not used,
            # we only set it to satisfy the Python type checker
            self.registered[full_topic] = handler
            self.client.subscribe(full_topic, qos=0)
            self.client.message_callback_add(full_topic, on_message)

    def on_connect(self,
                   client:mqtt.Client,
                   userdata:Any,
                   flags:Dict[str, int],
                   retcode:int) -> None:
        """ Called when the client connects to the broker, resubscribe to the
            sensorReporter topic.
            Gets automatically called from self.client after connection
            got fully established (on first connect and on reconnect)
        """
        refresh = "{}/{}".format(self.root_topic, REFRESH)
        self.log.info(
            "Connected with client %s, userdata %s, flags %s, and "
            "result code %s. Subscribing to refresh command topic %s",
            client,
            userdata,
            flags,
            retcode,
            refresh,
        )

        self.connected = True

        # Publish the ONLINE message to the LWT
        self._publish_mqtt(ONLINE, self.lwt, True)
        # send messages which got collected while connection was offline
        super().conn_went_online()

        # Resubscribe on connection
        for reg in self.registered:
            self.log.info("on_connect: Resubscribing to %s", reg)
            self.client.subscribe(reg)

        # causes sensors to republish their states
        self.msg_processor("MQTT connected")

    def on_disconnect(self,
                      client:mqtt.Client,
                      userdata:Any,
                      retcode:int) -> None:
        """ Called when the client disconnects from the broker. If the reason was
            not because disconnect() was called, try to reconnect.
        """
        self.log.info(
            "Disconnected from MQTT broker with client %s, userdata " "%s, and code %s",
            client,
            userdata,
            retcode,
        )

        self.connected = False
        super().conn_went_offline()
        if retcode != 0:
            self.log.error(
                "Unexpected disconnect code %s: %s reconnecting",
                retcode,
                mqtt.error_string(retcode),
            )
            self._connect()

    def on_publish(self,
                   client:mqtt.Client,
                   userdata:Any,
                   retcode:int) -> None:
        """ Called when a message is published. """
        self.log.debug(
            "on_publish: Successfully published message %s, %s, %s",
            client,
            userdata,
            retcode,
        )

    def on_subscribe(self,
                     client:mqtt.Client,
                     userdata:Any,
                     retcode:int,
                     qos:Tuple[int]) -> None:
        """ Called when a topic is subscribed to. """
        self.log.debug(
            "on_subscribe: Successfully subscribed %s, %s, %s, %s",
            client,
            userdata,
            retcode,
            qos,
        )
