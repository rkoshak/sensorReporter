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
import paho.mqtt.client as mqtt
from configparser import NoOptionError
from time import sleep
from core.connection import Connection

class MqttConnection(Connection):
    """Connects to and enables subscription and publishing to MQTT."""

    def __init__(self, msg_processor, log, params):
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
        super().__init__(msg_processor, log, params)

        self.log.info("Initializing MQTT Connection...")

        # Get the parameters, raises NoOptionError if one doesn't exist
        host = params("Host")
        port = int(params("Port"))
        client = params("Client")
        self.topic = params("Topic")
        tls = params("TLS").lower()
        self.log.info("tls = {}".format(tls))
        if tls == "yes" or tls == "true" or tls == "1":
            self.client.tls.set("./certs/ca.crt")
        user = params("User")
        passwd = params("Password")
        keepalive = int(params("Keepalive"))
        lwtt = params("LWT-Topic")

        # Initialize the client
        self.client = mqtt.Client(client_id=client, clean_session=False)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.msg_processor
        self.client.on_disconnect = self.on_disconnect
        self.client.username_pw_set(user, passwd)

        self.log.info("Attempting to connect to MQTT broker at {}:{}"
                      .format(host,port))
        connected = False
        while not connected:
            try:
                self.client.connect(host, port=port, keepalive=keepalive)
                connected = True
            except:
                import traceback
                self.log.error("Error connecting to {}:{}".format(host,port))
                self.log.debug("Exception: {}".format(traceback.format_exc()))
                sleep(5)

        self.log.info("Connection to MQTT is successful")

        self.client.will_set(lwtt, "OFFLINE", qos=0, retain=True)
        self.client.loop_start()

        self.registered = []

        # Publish the ONLINE message to the LWT
        self.publish("ONLINE", lwtt)

    def publish(self, message, topic):
        """Publishes message to topic, logging if there is an error."""
        try:
            rval = self.client.publish(topic, message)
            if rval[0] == mqtt.MQTT_ERR_NO_CONN:
                self.log.error("Error puiblishing update {} to {}"
                               .format(message, topic))
            else:
                self.log.info("Published message {} to {}"
                              .format(message, topic))
        except:
            import traceback
            self.log.error("Unexpected error publishing MQTT message: {}"
                           .format(traceback.format_exec()))

    def disconnect(self):
        """Closes the connection to the MQTT broker."""
        self.log.info("Disconnecting from MQTT")
        self.client.disconnect()

    def register(self, topic, handler):
        """Registers a handler to be called on messages received on topic."""
        self.log.info("Registering for messages on " + topic)
        self.registered.append((topic, handler))
        self.client.subscribe(topic)
        self.client.message_callback_add(topic, handler)

    def on_connect(self, client, userdata, flags, rc):
        """Called when the client connects to the broker, resubscribe to the
        sensorReporter topic.
        """
        self.log.info("Connected with result code {}, subscribing to command "
                      "topic {}".format(rc, self.topic))

        # Resubscribe on connection
        self.client.subscribe(self.topic)
        [self.client.subscribe(r[0]) for r in self.registered]

        # Act like we received a message on the command topic
        self.msg_processor(None, None, None)

    def on_disconnect(self, client, userdata, rc):
        """Called when the client disconnects from the broker. If the reason was
        not because disconnect() was called, try to reconnect.
        """
        self.log.info("Disconnected from MQTT broker with code {}".format(rc))

        if rc != 0:
            self.log.info("Unexpected disconnect code {}, reconnecting"
                          .format(rc))
