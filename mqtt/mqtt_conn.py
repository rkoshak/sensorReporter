import paho.mqtt.client as mqtt
from configparser import NoOptionError
from time import sleep
from core.connection import Connection

class MqttConnection(Connection):

    def __init__(self, msg_processor, log, params):

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

        self.log.info("Disconnecting from MQTT")
        self.client.disconnect()

    def register(self, topic, handler):

        self.log.info("Registering for messages on " + topic)
        self.registered.append((topic, handler))
        self.client.subscribe(topic)
        self.client.message_callback_add(topic, handler)

    def on_connect(self, client, userdata, flags, rc):

        self.log.info("Connected with result code {}, subscribing to command "
                      "topic {}".format(rc, self.topic))

        # Resubscribe on connection
        self.client.subscribe(self.topic)
        [self.client.subscribe(r[0]) for r in self.registered]

        # Act like we received a message on the command topic
        self.msg_processor(None, None, None)

    def on_disconnect(self, client, userdata, rc):

        self.log.info("Disconnected from MQTT broker with code {}".format(rc))

        if rc != 0:
            self.log.info("Unexpected disconnect code {}, reconnecting"
                          .format(rc))
