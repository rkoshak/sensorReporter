#!/usr/bin/python

"""
 Script: mqttReporter.py
 Author: Rich Koshak
 Date:   March 16, 2015
 Purpose: Log into the mqtt server and report updates to the sensors attached 
   to the configured pins. 1 is assumed to be open and 0 is closed.

  Signal Handling based on the code published here:
  http://stackoverflow.com/questions/14123592/implementing-signal-handling-on-a-sleep-loop
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import logging
import logging.handlers
import ConfigParser
import signal
import sys
import time
import webiopi
import paho.mqtt.client as mqtt
import paho.mqtt.publish as pub

# Globals
logger = logging.getLogger('mqttReporter')
client = mqtt.Client()
config = ConfigParser.ConfigParser()
sensors = []

#------------------------------------------------------------------------------
# Signal Handling
class BlockingAction(object):
    """Class to wrap a blocking function and record that the function is active. Used in conjunction with
       SignalHandler to properly handle termination signals. """

    def __new__(cls, action):
        """Wraps the passed in function in a BlockingAction unless it already is."""

        if isinstance(action, BlockingAction):
            return action
        else:
            new_action = super(BlockingAction, cls).__new__(cls)
            new_action.action = action
            new_action.active = False
            return new_action

    def __call__(self, *args, **kwargs):
        """Marks the function as active, calls it, then marks it as inactive"""

        self.active = True
        result = self.action(*args, **kwargs)
        self.active = False
        return result

class SignalHandler(object):
    """Handles termination signals by waiting for any active BlockingAction to complete before calling
       the cleanup function"""

    def __new__(cls, sig, action):
        """Wrap the passed in function in this object unless it is already wrapped."""

        if isinstance(action, SignalHandler):
            handler = action
        else:
            handler = super(SignalHandler, cls).__new__(cls)
            handler.action = action
            handler.blocking_actions = []
        signal.signal(sig, handler)
        return handler

    def __call__(self, signum, frame):
        """Wait for any active BlockingAction completes before calling the cleanup function"""

        while any(a.active for a in self.blocking_actions):
            time.sleep(.01)
        return self.action()

    def blocks_on(self, action):
        """Adds the passed in function as a BlockingAction"""

        blocking_action = BlockingAction(action)
        self.blocking_actions.append(blocking_action)
        return blocking_action

def handles(signal):
    """Called when a signal occurs. It wraps the SignalHandler so the decorator only has to pass the function."""

    def get_handler(action):

        return SignalHandler(signal, action)

    return get_handler

#------------------------------------------------------------------------------
# MQTT
def connect(user, password, host, p, ka):
    """Establishes the connection to the MQTT Broker"""
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.username_pw_set(user, password)
    client.connect(host, port=p, keepalive=ka)
    client.loop_start()

def on_connect(client, userdata, flags, rc):
    """Called when the MQQT client successfully connects to the broker"""
    logger.info("Connected with result code "+str(rc)+", subscribing to command topic " + config.get("MQTT", "Topic"))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed
    client.subscribe(config.get("MQTT", "Topic"))

    # Send the current states
    for s in sensors:
        s.checkState()
        s.publishState()

def on_message(client, userdata, msg):
    """Called when a message is received from the MQTT broker, send the current sensor state.
       We don't care what the message is."""
    
    logger.info("Received a request for current state, publishing")
    for s in sensors:
        s.checkState()
        s.publishState()

def on_disconnect(client, userdata, rc):
    """Called when the MQTT client disconnects from the broker"""
    logger.info("Disconnected from the MQTT broker with code " + str(rc))

    if rc != 0:
        logger.info("Unexpected disconnect: code = " + str(rc) + " reconnecting")
#        client.reconnect()
#        client.loop(timeout=0.5)

#------------------------------------------------------------------------------
# Initialization
def configLogger(file, size, num):
    """Configure a rotating log"""

    print "Configuring logger: file = " + file + " size = " + str(size) + " num = " + str(num)
    logger.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(file, mode='a', maxBytes=size, backupCount=num)
    formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info("---------------Started")

def loadConfig(configFile):
    """Read in the config file, set up the logger, and populate the sensors"""
    print "Loading " + configFile
    config.read(configFile)

    configLogger(config.get("Logging", "File"), 
                 config.getint("Logging", "MaxSize"), 
                 config.getint("Logging", "NumFiles"))

    logger.info("Connecting to MQTT Broker " + config.get("MQTT", "Host"))
    connect(config.get("MQTT", "User"), 
            config.get("MQTT", "Password"), 
            config.get("MQTT", "Host"), 
            config.getint("MQTT", "Port"), 
            config.getint("MQTT", "Keepalive"))

    logger.info("Populating the sensor's list")
    for section in config.sections():
        if section.startswith("Sensor"):
            sensors.append(Sensor(config.getint(section, "Pin"), 
                                  config.get(section, "Topic"),
                                  config.get(section, "PUD"),
                                  client))
#    client.loop(timeout=0.5)
    return sensors

#------------------------------------------------------------------------------
# Main Logic
class Sensor:
    """Represents a sensor connected to a GPIO pin"""

    def __init__(self, pin, topic, pud, comms):
        """Sets the sensor pin to pull up and publishes its current state"""

        logger.info("Setting up pin " + str(pin) + " on topic " + topic + " with PULL " + pud)
        self.gpio = webiopi.GPIO
        self.pin = pin
        pud = self.gpio.PUD_UP if pud=="UP" else self.gpio.PUD_DOWN
        self.gpio.setup(pin, self.gpio.IN, pull_up_down=pud)
        self.state = self.gpio.digitalRead(pin)
        self.topic = topic
        self.comms = comms
        #self.publishState()

    def checkState(self):
        """Publishes any state change"""

        value = self.gpio.digitalRead(self.pin)
        if(value != self.state):
            self.state = value
            self.publishState()

    def publishState(self):
        """Sends the current state to the MQTT broker"""

        sendVal = "CLOSED" if self.state == self.gpio.LOW else "OPEN" 
        rval = self.comms.publish(self.topic, sendVal)
        if rval[0] == mqtt.MQTT_ERR_NO_CONN:
            logger.error("Error publishing update to pin " + str(self.pin) + " to " + str(sendVal) + " on " + self.topic)
            self.comms.reconnect() # try to reconnect again 
            
        else:
            logger.info("Published update to pin " + str(self.pin) + " to " + str(sendVal) + " on " + self.topic) 

# The decorators below causes the creation of a SignalHandler attached to this function for each of the
# signals we care about using the handles function above. The resultant SignalHandler is registered with
# the signal.signal so cleanup_and_exit is called when they are received.
@handles(signal.SIGTERM)
@handles(signal.SIGHUP)
@handles(signal.SIGINT)
def cleanup_and_exit():
    """ Signal handler to ensure we disconnect cleanly in the event of a SIGTERM or SIGINT. """

    logger.warn("Terminiating the program")
    client.disconnect()
#    client.loop(timeout=0.5)
    logger.info("Successfully disconnected from the MQTT server")
    sys.exit(0)

# This decorator registers the function with the SignalHandler blocks_on so the SignalHandler knows
# when the function is running
@cleanup_and_exit.blocks_on
def publish(sensors):
    """Gets the current state of each sensor and publishes it"""

    for s in sensors:
        s.checkState()
#    client.loop(timeout=0.5) # allows the paho thread to connect to process

def main():
    """Polls the sensor pins and publishes any changes"""

    loadConfig(sys.argv[1])

    lastTime = time.time()
    while True:
        publish(sensors)
        diff = time.time() - lastTime
        if diff < 1:
            time.sleep(1-diff)
        else:
            time.sleep(0.1) # give the processor a chance if MQTT is being slow
        lastTime = time.time()

if __name__ == "__main__":
    main()


