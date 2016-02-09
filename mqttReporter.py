#!/usr/bin/python

"""
 Script: mqttReporter.py
 Author: Rich Koshak
 Date:   March 16, 2015
 Purpose: Log into the mqtt server and report updates to the sensors attached 
   to the configured pins. 1 is assumed to be open and 0 is closed.
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import logging
import logging.handlers
import ConfigParser
import signal
import sys
import time
import traceback
from threading import *

from signalProc import *
from mqttConn import mqttConnection
try:
    from bluetoothRSSIScanner import *
except ImportError:
    print 'Bluetooth is not supported on this machine'
try:
    from gpioSensor import *
except ImportError:
    print 'GPIO is not supported on this machine'
try:
    from dash import *
except ImportError:
    print 'Dash button detection is not supported on this machine'

# Globals
logger = logging.getLogger('mqttReporter')
mqttConn = mqttConnection()
config = ConfigParser.ConfigParser(allow_no_value=True)
sensors = []

# The decorators below causes the creation of a SignalHandler attached to this function for each of the
# signals we care about using the handles function above. The resultant SignalHandler is registered with
# the signal.signal so cleanup_and_exit is called when they are received.
@handles(signal.SIGTERM)
@handles(signal.SIGHUP)
@handles(signal.SIGINT)
def cleanup_and_exit():
    """ Signal handler to ensure we disconnect cleanly in the event of a SIGTERM or SIGINT. """

    logger.warn("Terminiating the program")
    mqttConn.client.disconnect()
    logger.info("Successfully disconnected from the MQTT server")
    sys.exit(0)

# This decorator registers the function with the SignalHandler blocks_on so the SignalHandler knows
# when the function is running
@cleanup_and_exit.blocks_on
def check(s):
    """Gets the current state of the passed in sensor and publishes it"""

    s.checkState()

def on_message(client, userdata, msg):
    """Called when a message is received from the MQTT broker, send the current sensor state.
       We don't care what the message is."""
    
    logger.info("Received a request for current state, publishing")
    for s in sensors:
        if s.poll > 0:
            s.checkState()
            s.publishState()

def main():
    """Polls the sensor pins and publishes any changes"""

    if len(sys.argv) < 2:
        print "No config file specified on the command line"
        sys.exit(1)

    loadConfig(sys.argv[1])
    for s in sensors:
        s.lastPoll = time.time()

    logger.info("Kicking off polling threads")
    lastTime = time.time()
    while True:
        diff = time.time() - lastTime

        # Kick off a poll of the sensor in a separate process
        for s in sensors:
            if s.poll > 0 and (time.time() - s.lastPoll) > s.poll:
                s.lastPoll = time.time()
                Thread(target=check, args=(s,)).start()
        
        if diff < .2:
            time.sleep(.2-diff)
        else:
            time.sleep(0.1) # give the processor a chance if MQTT is being slow
        lastTime = time.time()

#------------------------------------------------------------------------------
# Initialization
def configLogger(file, size, num):
    """Configure a rotating log"""

    print "Configuring logger: file = " + file + " size = " + str(size) + " num = " + str(num)
    logger.setLevel(logging.DEBUG)
    fh = logging.handlers.RotatingFileHandler(file, mode='a', maxBytes=size, backupCount=num)
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info("---------------Started")

def configMQTT(config):
    """Configure the MQTT connection"""

    logger.info("Connecting to MQTT Broker " + config.get("MQTT", "Host"))
    mqttConn.config(logger, config.get("MQTT", "User"), 
                    config.get("MQTT", "Password"), config.get("MQTT", "Host"), 
                    config.getint("MQTT", "Port"), config.getfloat("MQTT", "Keepalive"),
                    config.get("MQTT", "LWT-Topic"), config.get("MQTT", "LWT-Msg"),
                    config.get("MQTT", "Topic"), on_message)

def loadConfig(configFile):
    """Read in the config file, set up the logger, and populate the sensors"""

    print "Loading " + configFile
    config.read(configFile)

    configLogger(config.get("Logging", "File"), 
                 config.getint("Logging", "MaxSize"), 
                 config.getint("Logging", "NumFiles"))

    configMQTT(config)

    logger.info("Populating the sensor's list")
    for section in config.sections():
        if section.startswith("Sensor"):
            senType = config.get(section, "Type")
            if senType == "Bluetooth":
                sensors.append(btSensor(config.get(section, "Address"),
                                        config.get(section, "Topic"),
                                        mqttConn.publish, logger,
                                        config.getfloat(section, "Poll")))
            elif senType == "GPIO":
                sensors.append(gpioSensor(config.getint(section, "Pin"),
                                          config.get(section, "Topic"),
                                          config.get(section, "PUD"),
                                          mqttConn.publish, logger,
                                          config.getfloat(section, "Poll")))
            elif senType == "Dash":
                devices = {}
                i = 1
                addr = 'Address'+str(i)
                topic = 'Topic'+str(i)
                while config.has_option(section, addr):
                    devices[config.get(section, addr)] = config.get(section, topic)
                    i += 1
                    addr = 'Address'+str(i)
                    topic = 'Topic'+str(i)
                s = dash(devices, mqttConn.publish, logger, config.getint(section, "Poll"))
                sensors.append(s)
                Thread(target=s.checkState).start() # don't need to use cleanup-on-exit for this type

            else:
                logger.error(senType + " is an unknown sensor type")
    return sensors

if __name__ == "__main__":
    main()
