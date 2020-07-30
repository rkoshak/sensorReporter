import signal
import time
import sys
from configparser import ConfigParser, NoOptionError
import logging
import logging.handlers
import importlib
from core.poll_mgr import PollManager

def reload_configuration(signum, frame, config_file, pm):
    print('(SIGHUP) reading configuration')

    if pm:
        print("pm is {}".format(pm))
        pm.stop()
        pm = create_sensor_reporter(config_file)
        pm.start()
    else:
        print("pm is not set! {}".format(pm))

    return

def terminateProcess(signum, frame):
    print('(SIGTERM/SIGINT) terminating the process')
    sys.exit()

def init_logger(config):

    logger = logging.getLogger('SensorReporter')

    logger = logging.getLogger()
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    level = config.get("Logging", "Level", fallback="INFO")
    print("Setting logging level to {}".format(level))

    levels = {
      "CRITICAL": logging.CRITICAL,
      "ERROR"   : logging.ERROR,
      "WARNING" : logging.WARNING,
      "INFO"    : logging.INFO,
      "DEBUG"   : logging.DEBUG,
      "NOTSET"  : logging.NOTSET
    }

    logger.setLevel(levels.get(level, logging.NOTSET))

    if config.getboolean("Logging", "Syslog", fallback=True):
        print("Configuring syslogging")
        sh = logging.handlers.SysLogHandler('/dev/log',
                             facility=logging.handlers.SysLogHandler.LOG_SYSLOG)
        sh.encodePriority(sh.LOG_SYSLOG, sh.LOG_INFO)
        slFormatter = logging.Formatter('[SensorReporter] %(levelname)s - %(message)s')
        sh.setFormatter(slFormatter)
        logger.addHandler(sh)

    else:
        file = config.get("Logging", "File", fallback="/tmp/sensorReporter.log")
        size = int(config.get("Logging", "MaxSize", fallback="67108864"))
        num = int(config.get("Logging", "NumFiles", fallback="10"))
        print("Configuring logger: file = {} size = {} num = {}"
              .format(file, size, num))
        fh = logging.handlers.RotatingFileHandler(file, mode='a', maxBytes=size,
                                                  backupCount=num)
        formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.info("-----------------Logging Started")

    return logger

def create_connection(config, section, log):

    try:
        name = config.get(section, "Name")
        log.info("Creating connection {}".format(name))
        class_ = config.get(section, "Class")
        module_name, class_name = class_.rsplit(".", 1)
        conn = getattr(importlib.import_module(module_name), class_name)
        params = lambda key: config.get(section, key)
        return conn(on_message, log, params)
    except:
        import traceback
        log.error("Error creating connection {}: {}"
                  .format(section, traceback.format_exc()))
        return None

def create_device(config, section, log, connections):

    try:
        log.info("Creating device for {}".format(section))
        class_ = config.get(section, "Class")
        module_name, class_name = class_.rsplit(".", 1)
        Device = getattr(importlib.import_module(module_name), class_name)
        params = lambda key: config.get(section, key)

        dev_conns = []
        try:
            dev_conns = [connections[c] for c in params("Connection").split(",")]
        except NoOptionError:
            # An Actuator doesn't always have a connection
            pass

        return Device(dev_conns, log, params)
    except:
        import traceback
        log.error("Error creating device {}: {}"
                  .format(section, traceback.format_exc()))
        return None

def create_sensor_reporter(config_file):

    config = ConfigParser(allow_no_value=True)
    config.read(config_file)

    log = init_logger(config)

    # Create the connections
    connections = {}
    for section in [s for s in config.sections() if s.startswith("Connection")]:
        conn = create_connection(config, section, log)
        if conn:
            name = config.get(section, "Name")
            connections[name] = conn

    log.info("{} connections created".format(len(connections)))

    # Create the Actuators
    actuators = []
    for section in [s for s in config.sections() if s.startswith("Actuator")]:
        actuator = create_device(config, section, log, connections)
        if actuator:
            actuators.append(actuator)

    log.info("{} actuators created".format(len(actuators)))

    # Create the Sensors
    sensors = {}
    for section in [s for s in config.sections() if s.startswith("Sensor")]:
        sensor = create_device(config, section, log, connections)
        if sensor:
            sensors[section] = sensor

    log.info("{} sensors created".format(len(sensors)))

    # TODO create SR, SR is to start the polling threads
    log.info("Creating polling manager")
    pm = PollManager(connections, sensors, actuators, log)
    log.info("Created, returning polling manager")
    return pm

def on_message(client, userdata, msg, log):

    try:
        log.info("Received an update request")
        if msg:
            log.info("Topic: {} Message: {}".format(msg.topic, msg.payload))
        log.info("Getting current sensor states...")
        sr.report()
    except:
        import traceback
        log.error("Unexpected error: {}".format(traceback.format_exec()))

def main():

    if len(sys.argv) < 2:
        print("No config file specified on the command line! Usage: "
              "python3 sensorReporter.py [config].ini")
        sys.exit(1)

    config_file = sys.argv[1]
    print("Loading config file {}".format(config_file))
    pm = create_sensor_reporter(config_file)

    # Register functions to handle signals
    print("Registering for signals")
    signal.signal(signal.SIGHUP, lambda s, f : reload_configuration(s, f, config_file, pm)) # reload config
    signal.signal(signal.SIGTERM, terminateProcess)
    signal.signal(signal.SIGINT, terminateProcess) # CTRL-C

    # Starting polling loop
    print("Starting polling loop")
    pm.start()

if __name__ == '__main__':
    main()
