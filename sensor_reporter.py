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

""" The main script responsible for loading and parsing the yaml file, creating
    the polling manager and all of the connections, sensors, and actuators via
    reflection, and handling OS signals. On SIGINT it will exit. On SIGHUP it will
    stop and reload the config file to continue processing again.

Functions:
    - reload_configuration:  Called on SIGHUP, reloads the configuration
    - terminate_process:     Called on SIGINT and SIGTERM,
                             cleans up and exits the program
    - init_logger:           Initializes the logger based on the config in the .yml
    - create_connection:     Creates a Connection based on the config in the .yml
    - create_device:         Creates a Sensor or Actuator based on the config in the .yml
    - create_poll_manager:   Parses the yaml file and creates the logger,
                             connections, sensors, and actuators and polling manager
                             based on the config in the yaml file.
    - on_message:            called when a connection receives a message on the
                             sensor_reporter's topic
    - register_sig_handlers: Registers the reload_configuration and
                             terminate_process to be called on the appropriate OS signals
    - main:                  Verifies the command line arguments, call create_sensor_reporter,
                             registers for OS signals, and starts the polling manager.
"""
import signal
import sys
import traceback
import logging.handlers
import importlib
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
import yaml
from core.poll_mgr import PollManager
from core import utils
if TYPE_CHECKING:
    # Fix circular imports needed for the type checker
    from core import connection

logger = logging.getLogger("sensor_reporter")
glob_poll_mgr:Optional[PollManager] = None

def reload_configuration(signum:int,
                         frame:Any,
                         config_file:str) -> None:
    """ Called when a SIGHUP is received. Stops the polling manager and recreates
        it with the latest config file. Registers the signal handlers.
    """
    logger.info('(SIGHUP) reading configuration: %s %s', signum, frame)

    global glob_poll_mgr
    if glob_poll_mgr:
        glob_poll_mgr.stop()
        #cleanup glob_poll_mgr completely before starting over
        glob_poll_mgr = None
        glob_poll_mgr = create_poll_manager(config_file)
        register_sig_handlers(config_file, glob_poll_mgr)
        glob_poll_mgr.start()
    else:
        logger.info("poll_mgr is not set! %s", glob_poll_mgr)

def terminate_process(signum:int,
                      frame:Any,
                      poll_mgr:PollManager) -> None:
    """ Called when a SIGTERM or SIGINT is received, exits the program. """
    logger.info('(SIGTERM/SIGINT) terminating the process: %s %s', signum, frame)
    # TODO figure out how to set a timeout to wait for everything to exit
    poll_mgr.stop()
    sys.exit()

def register_sig_handlers(config_file:str,
                          poll_mgr:PollManager) -> None:
    """ Registers the signal handler functions with the passed in config_file
        and poll_mgr.
    """
    signal.signal(signal.SIGHUP,
                  lambda s, f: reload_configuration(s, f, config_file))
    signal.signal(signal.SIGTERM,
                  lambda s, f: terminate_process(s, f, poll_mgr))
    signal.signal(signal.SIGINT,
                  lambda s, f: terminate_process(s, f, poll_mgr))

def init_logger(logger_cfg:Dict[str, Any]) -> None:
    """ Initializes the logger based on the properties in the yaml file's Logging
        section.

    Properties:
        - "Level":    one of "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", or
                      "NOTSET", sets the logging level.
        - "Syslog":   When "True" (or other acceptable boolean representations of
                      True) logging is done to the syslog
        - "File":     only required when "Syslog" is False, the path to the file
                      to log to.
        - "MaxSize":  maximum size of the log file in bytes before rolling the
                      log file; only required when "SysLog" is False
        - "NumFiles": the number of rolled over log files to keep; only required
                      when "SysLog" is False
    """
    root_logger = logging.getLogger()
    while root_logger.hasHandlers():
        root_logger.removeHandler(root_logger.handlers[0])

    utils.set_log_level(logger_cfg, root_logger)

    formatter = logging.Formatter('%(asctime)s %(levelname)8s - [%(name)15.15s] %(message)s')

    # STDOUT logging
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    handler:Union[logging.handlers.SysLogHandler, logging.handlers.RotatingFileHandler]
    # Syslog logger
    if logger_cfg.get("Syslog", True):
        handler = logging.handlers.SysLogHandler(address='/dev/log',
                                                 facility=logging.handlers.SysLogHandler.LOG_SYSLOG)
        handler.encodePriority(handler.LOG_SYSLOG, handler.LOG_INFO)
        formatter = logging.Formatter('sensorReporter[%(process)s]: %(levelname)8s -'
                                      ' [%(name)15s] %(message)s')
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

    logger.info("Setting logging level to %s",
                logger_cfg.get("Level", "INFO"))

def create_connection(conn_cfg:Dict[str, Any],
                      section:str) -> Any:
    """ Creates a Connection using reflection based on the passed in section of
        the yaml file.
        Parameter:
            - dev_cfg        : The dictionary with the device configuration
            - section        : Section Name
        Returns:
            - None           : If the device could not be created due to an error
            - Class Object   : Object inheriting from the class core.connection
    """
    try:
        name = conn_cfg.get("Name")
        logger.info("Creating connection %s", name)
        class_ = str(conn_cfg.get("Class"))
        module_name, class_name = class_.rsplit(".", 1)
        conn = getattr(importlib.import_module(module_name), class_name)

        return conn(on_message, conn_cfg)
        # TODO create own exception to throw so we don't have to catch all
    except:
        logger.error("Error creating connection %s: %s",
                     section, traceback.format_exc())
        return None

def create_device(dev_cfg:Dict[str, Any],
                  section:str,
                  connections:Dict[str, 'connection.Connection']) -> Any:
    """ Creates a Sensor or Actuator using reflection based on the passed in
        section of the yaml file.
        Parameter:
            - dev_cfg        : The dictionary with the device configuration
            - section        : Section Name
            - connections    : Dictionary with connection objects
        Returns:
            - None           : If the device could not be created due to an error
            - Class Object   : Depending on the configuration passed,
                               a device inheriting from core.sensor or
                               core.actuator is returned
    """
    try:
        logger.info("Creating device for %s", section)
        class_ = str(dev_cfg.get("Class"))
        module_name, class_name = class_.rsplit(".", 1)
        device = getattr(importlib.import_module(module_name), class_name)

        dev_conns = {}
        try:
            dev_conns = {c:connections[c] for c in dev_cfg["Connections"].keys()}
        except KeyError as ex:
            # catch connection name typos at startup
            if "Connections" in ex.args:
                logger.error("Section 'Connections' missing for device %s", section)
                return None
            # If connections section is present the Key error is caused
            # by a misspelled connection name
            logger.error("Error creating device %s!"
                         " Probably the name of the connection %s is misspelled.",
                         section, ex)
            return None
        if 'Name' not in dev_cfg:
            #remember section name for logger messages within a device
            dev_cfg['Name'] = section.replace('Actuator', '').replace('Sensor','')

        return device(dev_conns, dev_cfg)
    except:
        logger.error("Error creating device %s: %s",
                     section, traceback.format_exc())
        return None

def create_poll_manager(config_file:str) -> PollManager:
    """ Loads and parses the config_file and based on it's contents initializes
        the logger, creates the Connections, Sensors, and Actuators, and creates
        the PollMgr to handle them all.
    """
    with open(config_file, 'r', encoding='utf_8') as file:
        try:
            config:Dict[str, Any] = yaml.safe_load(file)
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
            utils.spread_default_parameters(config, dev_cfg)
            actuator_dev = create_device(dev_cfg, section, connections)
            if actuator_dev:
                actuators.append(actuator_dev)

    logger.debug("%d actuators created", len(actuators))

    # Create the Sensors
    sensors = {}
    for (section, dev_cfg) in config.items():
        if section.startswith("Sensor"):
            utils.spread_default_parameters(config, dev_cfg)
            sensor_dev = create_device(dev_cfg, section, connections)
            if sensor_dev:
                sensors[section] = sensor_dev

    logger.debug("%d sensors created", len(sensors))

    #trigger auto discover messages
    for conn in connections.values():
        conn.publish_device_properties()

    logger.debug("Creating polling manager")
    poll_mgr = PollManager(connections, sensors, actuators)
    logger.debug("Created, returning polling manager")
    return poll_mgr

def on_message(msg:str) -> None:
    """ Called when a message to sensor_reporter is received on a Connection.
        Calls report on the poll_mgr, which will trigger all sensors to
        report their current reading.
    """
    try:
        if not glob_poll_mgr:
            logger.info("Received a request for current sensor states"
                        " before poll_mgr has been created, ignoring.")
            return
        if msg:
            logger.info("Message: %s", msg)
        logger.info("Getting current sensor states...")
        glob_poll_mgr.report()
    except:
        logger.error("Unexpected error: %s", traceback.format_exc())

def main() -> None:
    """" The main function, creates everything and starts the polling loop. """

    if len(sys.argv) < 2:
        print("No config file specified on the command line! Usage: "
              "bin/python sensorReporter.py [config].yml")
        sys.exit(1)

    config_file = sys.argv[1]
    global glob_poll_mgr
    glob_poll_mgr = create_poll_manager(config_file)

    # Register functions to handle signals
    register_sig_handlers(config_file, glob_poll_mgr)

    # Starting polling loop
    glob_poll_mgr.start()

if __name__ == '__main__':
    main()
