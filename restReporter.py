#!/usr/bin/python

"""
 Script:  restReporter.py
 Author:  Lenny Shirley <http://www.lennysh.com>
 Date:    February 8, 2016
 Purpose: Uses the OpenHAB REST API to report updates to the configured sensors
"""

import logging
import logging.handlers
import ConfigParser
import sys
import time
import traceback
from threading import *

from restConn import restConnection
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
logger = logging.getLogger('restReporter')
restConn = restConnection()
config = ConfigParser.ConfigParser(allow_no_value=True)
sensors = []

def cleanup_and_exit():
    logger.warn("Terminating the program...")

def check(s):
    """Gets the current state of the passed in sensor and publishes it"""
    s.checkState()

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

    configREST(config.get("REST", "URL"))

    logger.info("Populating the sensor's list...")
    for section in config.sections():
        if section.startswith("Sensor"):
            senType = config.get(section, "Type")
            if senType == "Bluetooth":
                sensors.append(btSensor(config.get(section, "Address"),
                                        config.get(section, "Topic"),
                                        restConn.publish, logger,
                                        config.getfloat(section, "Poll")))
            elif senType == "GPIO":
                sensors.append(gpioSensor(config.getint(section, "Pin"),
                                          config.get(section, "Topic"),
                                          config.get(section, "PUD"),
                                          restConn.publish, logger,
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
                s = dash(devices, restConn.publish, logger, config.getint(section, "Poll"))
                sensors.append(s)
                Thread(target=s.checkState).start() # don't need to use cleanup-on-exit for this type

            else:
                logger.error(senType + " is an unknown sensor type")
    return sensors

if __name__ == "__main__":
    main()
