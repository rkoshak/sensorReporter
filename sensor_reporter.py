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

"""The main script responsible for loading and parsing the .ini file, creating
the polling manager and all of the connections, sensors, and actuators via
reflection, and handling OS signals. On SIGINT it will exit. On SIGHUP it will
stop and reload the config file to contine processing again.

Functions:
    - reload_configuration: Called on SIGHUP, reloads the configuration
    - terminate_process: Called on SIGINT and SIGTERM, cleans up and exits the
    program
    - init_logger: Initializes the logger based on the config in the .ini
    - create_connection: Creates a Connection based on the config in the .ini
    - create_device: Creates a Sensor or Actuator based on the config in the .ini
    - create_poll_manager: Parses the .ini file and creates the logger,
    connections, sensors, and actuators and polling manager based on the config
    in the yaml.
    - on_message: called when a connection receives a message on the
    sensor_reporter's topic
    - register_sig_handlers: Registers the reload_configuration and
    terminate_process to be called on the appropriate OS signals
    - main: Verifies the command line arguments, call create_sensor_reporter,
    registers for OS signals, and starts the polling manager.
"""
import signal
import sys
import traceback
import logging.handlers
import importlib
import yaml
from core.poll_mgr import PollManager
from core.utils import set_log_level, spread_default_parameters

logger = logging.getLogger("sensor_reporter")
poll_mgr = None

def reload_configuration(signum, frame, config_file):
    """Called when a SIGHUP is received. Stops the polling manager and recreates
    it with the latest config file. Reregisters the signal handlers.
    """
    logger.info('(SIGHUP) reading configuration: {} {}'.format(signum, frame))

    global poll_mgr
    if poll_mgr:
        poll_mgr.stop()
        #cleanup poll_mgr compleatly befor starting over
        poll_mgr = None
        poll_mgr = create_poll_manager(config_file)
        register_sig_handlers(config_file, poll_mgr)
        poll_mgr.start()
    else:
        logger.info("poll_mgr is not set! {}".format(poll_mgr))

def terminate_process(signum, frame, poll_mgr):
    """Called when a SIGTERM or SIGINT is received, exits the program."""
    logger.info('(SIGTERM/SIGINT) terminating the process: {} {}'.format(signum, frame))
    # TODO figure out how to set a timeout to wait for everything to exit
    poll_mgr.stop()
    sys.exit()

def register_sig_handlers(config_file, poll_mgr):
    """Registers the singal handler functions with the passed in config_file
    and poll_mgr.
    """
    signal.signal(signal.SIGHUP,
                  lambda s, f: reload_configuration(s, f, config_file))
    signal.signal(signal.SIGTERM,
                  lambda s, f: terminate_process(s, f, poll_mgr))
    signal.signal(signal.SIGINT,
                  lambda s, f: terminate_process(s, f, poll_mgr))

def init_logger(logger_cfg):
    """Initializes the logger based on the properties in the yaml file's Logging
    section.

    Properties:
        - "Level": one of "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or
        "NOTSET", sets the logging level.
        - "Syslog": When "True" (or other acceptable boolean representations of
        True) logging is done to the syslog
        - "File": only required when "Syslog" is False, the path to the file to
        log to.
        - "MaxSize": maximum size of the log file in bytes before rolling the
        log file; only required when "SysLog" is False
        - "NumFiles": the number of rolled over log files to keep; only required
        when "SysLog" is False
    """
    root_logger = logging.getLogger()
    while root_logger.hasHandlers():
        root_logger.removeHandler(root_logger.handlers[0])

    set_log_level(logger_cfg, root_logger)

    formatter = logging.Formatter('%(asctime)s %(levelname)8s - [%(name)15.15s] %(message)s')

    # Syslog logger
    if logger_cfg.get("Syslog", True):
        handler = logging.handlers.SysLogHandler('/dev/log',
                                                 facility=logging.handlers.SysLogHandler.LOG_SYSLOG)
        handler.encodePriority(handler.LOG_SYSLOG, handler.LOG_INFO)
        formatter = logging.Formatter('%(levelname)s - [%(name)s] %(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    else:
        # File logging
        file = logger_cfg.get("File", "/tmp/sensorReporter.log")
        size = int(logger_cfg.get("MaxSize", "67108864"))
        num = int(logger_cfg.get("NumFiles", "10"))
        handler = logging.handlers.RotatingFileHandler(file, mode='a',
                                                       maxBytes=size,
                                                       backupCount=num)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        # STDOUT logging
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

    logger.info("Setting logging level to {}"
                .format(logger_cfg.get("Level", "INFO")))

def create_connection(conn_cfg, section):
    """Creates a Connection using reflection based on the passed in section of
    the yaml file.
    """
    try:
        name = conn_cfg.get("Name")
        logger.info("Creating connection {}".format(name))
        class_ = conn_cfg.get("Class")
        module_name, class_name = class_.rsplit(".", 1)
        conn = getattr(importlib.import_module(module_name), class_name)
        return conn(on_message, conn_cfg)
        # TODO create own exception to throw so we don't have to catch all
    except:
        logger.error("Error creating connection {}: {}"
                     .format(section, traceback.format_exc()))
        return None

def create_device(dev_cfg, section, connections):
    """Creates a Sensor or Actuator using reflection based on the passed in
    section of the yaml file.
    """
    try:
        logger.info("Creating device for {}".format(section))
        class_ = dev_cfg.get("Class")
        module_name, class_name = class_.rsplit(".", 1)
        device = getattr(importlib.import_module(module_name), class_name)

        dev_conns = {}
        try:
            dev_conns = {c:connections[c] for c in dev_cfg["Connections"].keys()}
        except KeyError as ex:
            # catch connection name typos at startup
            if "Connections" in ex.args:
                logger.error("Section 'Connections' missing for device {}".format(section))
                return None
            # If connections section is present the Key error is caused
            # by a misspelled connection name
            logger.error("Error creating device {}!"
                         " Probably the name of the connection {} is misspelled."
                         .format(section, ex))
            return None
        if 'Name' not in dev_cfg:
            #remember section name for logger messages within a device
            dev_cfg['Name'] = section.replace('Actuator', '').replace('Sensor','')

        return device(dev_conns, dev_cfg)
    except:
        logger.error("Error creating device {}: {}"
                     .format(section, traceback.format_exc()))
        return None

def create_poll_manager(config_file):
    """Loads and parses the config_file and based on it's contents initializes
    the logger, creates the Connections, Sensors, and Actuators, and creates
    the PollMgr to handle them all.
    """
    with open(config_file, 'r', encoding='utf_8') as file:
        try:
            config = yaml.safe_load(file)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError):
            # yaml.scanner.ScannerError: YAML reports: "mapping values are not allowed here"
            # This is caused by wrong indentation of the first value
            # after a Sensor, Actuator, Connection definition

            # yaml.parser.ParserError: YAML reports: "while parsing a block mapping"
            # This is paused by wrong indentation in the middle lower part of a
            # device definition (Sensor, Actuator, Connection)
            logger.error("YAML-Config indentation error: Make sure that the indentation is"
                         " the same for each level of configuration values!")
            sys.exit(1)

    init_logger(config["Logging"])

    # Create the connections
    connections = {}
    for (section, conn_cfg) in config.items():
        if section.startswith("Connection"):
            conn = create_connection(conn_cfg, section)
            if conn:
                name = conn_cfg.get("Name")
                connections[name] = conn

    logger.debug("%d connections created", len(connections))

    # Create the Actuators
    actuators = []
    for (section, dev_cfg) in config.items():
        if section.startswith("Actuator"):
            spread_default_parameters(config, dev_cfg)
            actuator = create_device(dev_cfg, section, connections)
            if actuator:
                actuators.append(actuator)

    logger.debug("%d actuators created", len(actuators))

    # Create the Sensors
    sensors = {}
    for (section, dev_cfg) in config.items():
        if section.startswith("Sensor"):
            spread_default_parameters(config, dev_cfg)
            sensor = create_device(dev_cfg, section, connections)
            if sensor:
                sensors[section] = sensor

    logger.debug("%d sensors created", len(sensors))

    #trigger auto discover messages
    for conn in connections.values():
        conn.publish_device_properties()

    logger.debug("Creating polling manager")
    poll_mgr = PollManager(connections, sensors, actuators)
    logger.debug("Created, returning polling manager")
    return poll_mgr

def on_message(msg):
    """Called when a message to sensor_reporter is received on a Connection.
    Calls report on the poll_mgr.
    """
    try:
        if not poll_mgr:
            logger.info("Received a request for current sensor states"
                        " before poll_mgr has been created, ignoring.")
            return
        if msg:
            logger.info("Message: {}".format(msg))
        logger.info("Getting current sensor states...")
        poll_mgr.report()
    except:
        logger.error("Unexpected error: {}".format(traceback.format_exc()))

def main():
    """"The main function, creates everything and starts the polling loop."""

    if len(sys.argv) < 2:
        print("No config file specified on the command line! Usage: "
              "python3 sensorReporter.py [config].ini")
        sys.exit(1)

    config_file = sys.argv[1]
    global poll_mgr
    poll_mgr = create_poll_manager(config_file)

    # Register functions to handle signals
    register_sig_handlers(config_file, poll_mgr)

    # Starting polling loop
    poll_mgr.start()

if __name__ == '__main__':
    main()
