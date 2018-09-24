"""
   Copyright 2015 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: mqttConn.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Provides and maintains a connection to the MQTT broker
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import sys
import paho.mqtt.client as mqtt
from time import sleep

class mqttConnection(object):
  """Centralizes the MQTT logic"""

  def __init__(self, msgProc, logger, params, sensors, actuators):
    """Creates and connects to the MQTT broker"""

    self.logger = logger
    self.msgProc = msgProc # function that gets called when a message is received

    self.logger.info("Configuring MQTT connection to broker %s:%s" % (params("Host"), params("Port")))

    self.topic = params("Topic")

    self.client = mqtt.Client(client_id=params("Client"), clean_session=False)
    if params("TLS") == "YES":
      self.client.tls_set("./certs/ca.crt")
    self.client.on_connect = self.on_connect
    self.client.on_message = self.msgProc
    self.client.on_disconnect = self.on_disconnect
    self.client.username_pw_set(params("User"), params("Password"))

    self.logger.info("Attempting to connect to MQTT broker at " + params("Host") + ":" + params("Port"))
    connected = False
    while not  connected:
      try:
        self.client.connect(params("Host"), port=int(params("Port")), keepalive=float(params("Keepalive")))
        connected = True
      except:
        self.logger.error("Error connecting to " + params("Host") + ":" + params("Port"))
        sleep(5) # wait five seconds before retrying

    self.logger.info("Connection successful")

    self.client.will_set(params("LWT-Topic"), params("LWT-Msg"), 0, False)
    self.client.loop_start()
    
    self.registered = []

  def publish(self, message, pubTopic):
    """Called by others to publish a message to the publish topic"""

    try:
      rval = self.client.publish(pubTopic, message)
      if rval[0] == mqtt.MQTT_ERR_NO_CONN:
        self.logger.error("Error publishing update: " + message +  " to " + pubTopic)
        self.comms.reconnect() # try to reconnect again
      else:
        self.logger.info("Published message " + message + " to " + pubTopic)
    except:
      print "Unexpected error publishing message:", sys.exc_info()[0]

  def register(self, subTopic, msgHandler):
    """Registers an actuator to receive messages"""
    self.logger.info("Registering for messages on " + subTopic)
    self.registered.append((subTopic, msgHandler))
    self.client.subscribe(subTopic)
    self.client.message_callback_add(subTopic, msgHandler)

  def on_connect(self, client, userdata, flags, rc):
    """Called when the MQQT client successfully connects to the broker"""

    self.logger.info("Connected with result code "+str(rc)+", subscribing to command topic " + self.topic)
        
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed
    self.client.subscribe(self.topic)

    for r in self.registered:
      self.client.subscribe(r[0])

    self.msgProc(None, None, None)

  def on_disconnect(self, client, userdata, rc):
    """Called when the MQTT client disconnects from the broker"""

    self.logger.info("Disconnected from the MQTT broker with code " + str(rc))

    if rc != 0:
      self.logger.info("Unexpected disconnect: code = " + str(rc) + " reconnecting")

  def disconnect(self):
    """Called when the system is closing down"""

    self.logger.info("Disconnecting from the MQTT broker")
    self.client.disconnect()
