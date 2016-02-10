#!/usr/bin/python

"""
 Script:  sensorReporter.py
 Author:  Rich Koshak / Lenny Shirley <http://www.lennysh.com>
 Date:    February 10, 2016
 Purpose: Uses the REST API or MQTT to report updates to the configured sensors
"""

import logging
import logging.handlers
import ConfigParser
import signal
import sys
import time
import traceback
from threading import *

try:
    from restConn import restConnection
    restSupport = True
except:
    restSupport = False
    print 'REST required files not found. REST not supported in this script.'
try:
    from mqttConn import mqttConnection
    mqttSupport = True
except:
    mqttSupport = False
    print 'MQTT required files not found. MQTT not supported in this script.'
try:
    from bluetoothRSSIScanner import *
    bluetoothSupport = True
except ImportError:
    bluetoothSupport = False
    print 'Bluetooth is not supported on this machine'
try:
    from signalProc import *
    from gpioSensor import *
    gpioSupport = True
except ImportError:
    gpioSupport = False
    print 'GPIO is not supported on this machine'
try:
    from dash import *
    dashSupport = True
except ImportError:
    dashSupport = False
    print 'Dash button detection is not supported on this machine'

# Globals
logger = logging.getLogger('sensorReporter')
if restSupport:
    restConn = restConnection()
if mqttSupport:
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

    logger.warn("Terminating the program")
    try:
        mqttConn.client.disconnect()
        logger.info("Successfully disconnected from the MQTT server")
    except:
        pass
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
        print "No config file specified on the command line!"
        sys.exit(1)

    loadConfig(sys.argv[1])
    for s in sensors:
        s.lastPoll = time.time()

    logger.info("Kicking off polling threads...")
    #lastTime = time.time()
    while True:
        #diff = time.time() - lastTime

        # Kick off a poll of the sensor in a separate process
        for s in sensors:
            if s.poll > 0 and (time.time() - s.lastPoll) > s.poll:
                s.lastPoll = time.time()
                Thread(target=check, args=(s,)).start()
        
        time.sleep(0.5) # give the processor a chance if REST is being slow
        #lastTime = time.time()

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

    logger.info("Configuring the MQTT Broker " + config.get("MQTT", "Host"))
    mqttConn.config(logger, config.get("MQTT", "User"), 
                    config.get("MQTT", "Password"), config.get("MQTT", "Host"), 
                    config.getint("MQTT", "Port"), config.getfloat("MQTT", "Keepalive"),
                    config.get("MQTT", "LWT-Topic"), config.get("MQTT", "LWT-Msg"),
                    config.get("MQTT", "Topic"), on_message)

def configREST(url):
    """Configure the REST connection"""	
    restConn.config(logger, url)
    logger.info("REST URL set to: " + url)

def loadConfig(configFile):
    """Read in the config file, set up the logger, and populate the sensors"""
    print "Loading " + configFile
    config.read(configFile)

    configLogger(config.get("Logging", "File"), 
                 config.getint("Logging", "MaxSize"), 
                 config.getint("Logging", "NumFiles"))

    if restSupport:
        configREST(config.get("REST", "URL"))
    if mqttSupport:
        configMQTT(config)

    logger.info("Populating the sensor's list...")
    for section in config.sections():
        if section.startswith("Sensor"):
            senType = config.get(section, "Type")
            rptType = config.get(section, "ReportType")
            if rptType == "REST" and restSupport:
                typeConn = restConn
            elif rptType == "MQTT" and mqttSupport:
                typeConn = mqttConn
            else:
                if senType == "Dash":
				    msg = "Skipping 'Dash' sensors due to lack of support in the script for 'Dash'. Please see preceding error messages."
                else:
                    msg = "Skipping sensor '%s' due to lack of support in the script for '%s'. Please see preceding error messages." % (config.get(section, "Destination"), rptType)
                print msg
                logger.warn(msg)
                continue

            if senType == "Bluetooth" and bluetoothSupport:
                sensors.append(btSensor(config.get(section, "Address"),
                                        config.get(section, "Destination"),
                                        typeConn.publish, logger,
                                        config.getfloat(section, "Poll")))
            elif senType == "GPIO" and gpioSupport:
                sensors.append(gpioSensor(config.getint(section, "Pin"),
                                          config.get(section, "Destination"),
                                          config.get(section, "PUD"),
                                          typeConn.publish, logger,
                                          config.getfloat(section, "Poll")))
            elif senType == "Dash" and dashSupport:
                devices = {}
                i = 1
                addr = 'Address'+str(i)
                destination = 'Destination'+str(i)
                while config.has_option(section, addr):
                    i += 1
                    addr = 'Address'+str(i)
                    destination = 'Destination'+str(i)
                    rptType = 'ReportType'+str(i)
                s = dash(devices, typeConn.publish, logger, config.getint(section, "Poll"))
                sensors.append(s)
                Thread(target=s.checkState).start() # don't need to use cleanup-on-exit for this type

            else:
                msg = "Either '%s' is an unknown sensor type, not supported in this script, or '%s' is not supported in this script.  Please see preceding error messages to be sure." % (senType, rptType)
                print msg
                logger.error(msg)
    return sensors

if __name__ == "__main__":
    main()
