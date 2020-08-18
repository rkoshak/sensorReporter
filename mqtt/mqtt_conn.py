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
import paho.mqtt.client as mqtt
from core.connection import Connection

LWT = "status"
REFRESH = "refresh"
ONLINE = "ONLINE"
OFFLINE = "OFFLINE"

class MqttConnection(Connection):
    """Connects to and enables subscription and publishing to MQTT."""

    def __init__(self, msg_processor, params):
        """Establishes the MQTT connection and starts the MQTT thread. Exepcts
        the following parameters in params:
        - "Host": hostname or IP address of the MQTT broker
        - "Port": port for the MQTT broker
        - "Client": client ID to register with the MQTT broker, must be unique
        - "RootTopic": root topic that will be the vase of the topic hierarchy
        this connection subscribes and publishes to.
        - "TLS": optional parameters to determine if the connection should be
        encrypted using TLS. If set, the ca.crt file must be placed in
        ./certs/ca.crt
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
        super().__init__(msg_processor, params)
        self.log.info("Initializing MQTT Connection...")

        # Get the parameters, raises NoOptionError if one doesn't exist
        self.host = params("Host")
        self.port = int(params("Port"))
        client_name = params("Client")
        self.root_topic = params("RootTopic")
        tls = params("TLS").lower()
        user = params("User")
        passwd = params("Password")
        self.keepalive = int(params("Keepalive"))

        # Initialize the client
        self.client = mqtt.Client(client_id=client_name, clean_session=True)
        if tls in ('yes', 'true', '1'):
            self.log.debug("TLS is true, configuring certificates")
            self.client.tls_set("./certs/ca.crt")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.username_pw_set(user, passwd)

        self.log.info("Attempting to connect to MQTT broker at %s:%s", host, port)
        self.connected = False
#        while not self.connected:
#            try:
#                self.client.connect(host, port=port, keepalive=keepalive)
#                self.connected = True
#            except socket.gaierror:
#                self.log.error("Error connecting to %s:%s", host, port)
#                self.log.debug("Exception: %s", traceback.format_exc())
#                sleep(5)
#
#        self.log.info("Connection to MQTT is successful")
        self._connect()

        lwtt = "{}/{}".format(self.root_topic, LWT)
        ref = "{}/{}".format(self.root_topic, REFRESH)

        self.log.info("LWT topic is %s, subscribing to refresh topic %s",
                      lwtt, ref)
        self.client.will_set(lwtt, OFFLINE, qos=2, retain=True)
        self.register(REFRESH, msg_processor)

        self.client.loop_start()
        self._publish_mqtt(ONLINE, LWT, True)

    def _connect(self):
        while not self.connected:
            try:
                self.client.connect(self.host, self.port=port, self.keepalive=keepalive)
                self.connected = True
            except socket.gaierror:
                self.log.error("Error connecting to %s:%s", self.host, self.port)
                self.log.debug("Exception: %s", traceback.format_exc())
                sleep(5)

        self.log.info("Connection to MQTT is successful")


    def publish(self, message, destination):
        """Publishes message to destination, logging if there is an error."""
        self._publish_mqtt(message, destination, False)

    def _publish_mqtt(self, message, topic, retain):
        try:
            if not self.connected:
                self.log.warning("MQTT is not currently connected! Ignoring message")
                return
            full_topic = "{}/{}".format(self.root_topic, topic)
            rval = self.client.publish(full_topic, message, retain=retain)
            if rval[0] == mqtt.MQTT_ERR_NO_CONN:
                self.log.error("Error puiblishing update %s to %s", message, full_topic)
            else:
                self.log.debug("Published message %s to %s retain=%s", message, full_topic, retain)
        except ValueError:
            self.log.error("Unexpected error publishing MQTT message: %s",
                           traceback.format_exc())

    def disconnect(self):
        """Closes the connection to the MQTT broker."""
        self.log.info("Disconnecting from MQTT")
        self._publish_mqtt(OFFLINE, LWT, True)
        self.client.disconnect()

    def register(self, destination, handler):
        """Registers a handler to be called on messages received on topic
        appended to the root_topic. Handler is expected to take one argument,
        the message.
        """
        full_topic = "{}/{}".format(self.root_topic, destination)
        self.log.info("Registering for messages on %s", full_topic)

        def on_message(client, userdata, msg):
            self.log.debug("Received message client %s userdata %s and msg %s",
                           client, userdata, msg)
            handler(msg.payload.decode("utf-8"))

        self.registered[full_topic] = on_message
        self.client.subscribe(full_topic)
        self.client.message_callback_add(full_topic, on_message)

    def on_connect(self, client, userdata, flags, retcode):
        """Called when the client connects to the broker, resubscribe to the
        sensorReporter topic.
        """
        refresh = "{}/{}".format(self.root_topic, REFRESH)
        self.log.info("Connected with client %s, userdata %s, flags %s, and "
                      "result code %s. Subscribing to refresh command topic %s",
                      client, userdata, flags, retcode, refresh)

        self.connected = True

        # Publish the ONLINE message to the LWT
        self._publish_mqtt(ONLINE, LWT, True)

        # Resubscribe on connection
        for reg in self.registered:
            self.client.subscribe(self.registered[reg])

        self.registered[refresh]("connected")

    def on_disconnect(self, client, userdata, retcode):
        """Called when the client disconnects from the broker. If the reason was
        not because disconnect() was called, try to reconnect.
        """
        self.log.info("Disconnected from MQTT broker with client %s, userdata "
                      "%s, and code %s", client, userdata, retcode)

        self.connected = False
        if retcode != 0:
            codes = {1: "incorrect protocol verison",
                     2: "invalid client identifier",
                     3: "server unavailable",
                     4: "bad username or password",
                     5: "not authorized"}
            self.log.error("Unexpected disconnect code %s: %s, reconnecting",
                           retcode, codes[retcode])
            self._connect()
