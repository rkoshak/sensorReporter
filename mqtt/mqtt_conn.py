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
import logging
import paho.mqtt.client as mqtt
from core.connection import Connection
from core.utils import set_log_level

log = logging.getLogger(__name__.split(".")[1])

class MqttConnection(Connection):
    """Connects to and enables subscription and publishing to MQTT."""

    def __init__(self, msg_processor, params):
        """Establishes the MQTT connection and starts the MQTT thread. Exepcts
        the following parameters in params:
        - "Host": hostname or IP address of the MQTT broker
        - "Port": port for the MQTT broker
        - "Client": client ID to register with the MQTT broker, must be unique
        - "Topic": topic to subscribe to for messages directed at sensor_reporter
        itself as opposed to individual sensors or actuators
        - "TLS": optional parameters to determine if the connection should be
        encrypted using TLS. If set, the ca.crt file must be placed in
        ./certs/ca.crt
        - "User": MQTT broker login user name
        - "Password": MQTT broker login password
        - "Keepalive": MQTT keepalive parameter
        - "LWT-TOPIC": MQTT topic, when started "ONLINE" is published as a
        retained message and "OFFLINE" is registered as the LWT message.

        If the connection fails, it will keep retrying every five seconds until
        the connection is successful.
        """
        super().__init__(msg_processor, params)
        set_log_level(params, log)
        log.info("Initializing MQTT Connection...")

        # Get the parameters, raises NoOptionError if one doesn't exist
        host = params("Host")
        port = int(params("Port"))
        client_name = params("Client")
        self.topic = params("Topic")
        tls = params("TLS").lower()
        log.info("tls = {}".format(tls))
        user = params("User")
        passwd = params("Password")
        keepalive = int(params("Keepalive"))
        lwtt = params("LWT-Topic")

        # Initialize the client
        self.client = mqtt.Client(client_id=client_name, clean_session=True)
        if tls in ('yes', 'true', '1'):
            log.debug("TLS is true, configuring certificates")
            self.client.tls_set("./certs/ca.crt")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.msg_processor
        self.client.on_disconnect = self.on_disconnect
        self.client.username_pw_set(user, passwd)

        log.info("Attempting to connect to MQTT broker at {}:{}"
                      .format(host, port))
        self.connected = False
        while not self.connected:
            try:
                self.client.connect(host, port=port, keepalive=keepalive)
                self.connected = True
            except socket.gaierror:
                log.error("Error connecting to {}:{}".format(host, port))
                log.debug("Exception: {}".format(traceback.format_exc()))
                sleep(5)

        log.info("Connection to MQTT is successful")

        self.client.will_set(lwtt, "OFFLINE", qos=2, retain=True)
        self.client.loop_start()

        self.registered = []

        # Publish the ONLINE message to the LWT
        self.publish("ONLINE", lwtt)

    def publish(self, message, topic):
        """Publishes message to topic, logging if there is an error."""
        try:
            if not self.connected:
                log.warn("MQTT is not currently connected! Ignoring message")
                return

            rval = self.client.publish(topic, message)
            if rval[0] == mqtt.MQTT_ERR_NO_CONN:
                log.error("Error puiblishing update {} to {}"
                          .format(message, topic))
            else:
                log.info("Published message {} to {}"
                         .format(message, topic))
        except ValueError:
            log.error("Unexpected error publishing MQTT message: {}"
                      .format(traceback.format_exc()))

    def disconnect(self):
        """Closes the connection to the MQTT broker."""
        log.info("Disconnecting from MQTT")
        self.client.disconnect()

    def register(self, topic, handler):
        """Registers a handler to be called on messages received on topic."""
        log.info("Registering for messages on " + topic)
        self.registered.append((topic, handler))
        self.client.subscribe(topic)
        self.client.message_callback_add(topic, handler)

    def on_connect(self, client, userdata, flags, retcode):
        """Called when the client connects to the broker, resubscribe to the
        sensorReporter topic.
        """
        log.info("Connected with client {}, userdata {}, flags {}, and "
                 "result code {}. Subscribing to command topic {}"
                 .format(client, userdata, flags, retcode, self.topic))

        self.connected = True
        # Resubscribe on connection
        self.client.subscribe(self.topic)
        for reg in self.registered:
            self.client.subscribe(reg[0])

        # Act like we received a message on the command topic
        self.msg_processor(None, None, None)

    def on_disconnect(self, client, userdata, retcode):
        """Called when the client disconnects from the broker. If the reason was
        not because disconnect() was called, try to reconnect.
        """
        log.info("Disconnected from MQTT broker with client {}, userdata "
                 "{}, and code {}".format(client, userdata, retcode))

        self.connected = False
        if retcode != 0:
            codes = { 1: "incorrect protocol verison",
                      2: "invalid client identifier",
                      3: "server unavailable",
                      4: "bad username or password",
                      5: "not authorized"}
            log.error("Unexpected disconnect code {}:{}, reconnecting"
                      .format(retcode, codes[retcode]))
