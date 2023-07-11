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

"""Contains the parent class for Sensors.

Classes: Sensor
"""

from abc import ABC
import logging
from core.utils import set_log_level, DEFAULT_SECTION


class Sensor(ABC):
    """Abstract class from which all sensors should inherit. check_state and/or
    publish_state should be overridden.
    """

    def __init__(self, publishers, dev_cfg):
        """
        Sets all the passed in arguments as data members. If params("Poll")
        exists self.poll will be set to that. If not it is initialized to -1.
        self.last_poll is initialied to None.

        Arguments:
        - publishers: list of Connection objects to report to.
        - dev_cfg: parameters from the section in the yaml file the sensor is created
        from.

        Important Parameters:
        - self.comm: communication dictionary, with information where to publish
                     contains connection named dictionarys for each connection
        - self.log: The log instance for this device
        - self.poll: The poll interval in seconds
        - self.name: device name, usful for log entries
        """
        self.log = logging.getLogger(type(self).__name__)
        self.publishers = publishers
        self.comm = dev_cfg['Connections']
        self.dev_cfg = dev_cfg
        #Sensor Name is specified in sensor_reporter.py > creat_device()
        self.name = dev_cfg.get('Name')
        self.poll = float(dev_cfg.get("Poll", -1))

        self.last_poll = None
        set_log_level(dev_cfg, self.log)


    def _register(self, comm):
        """Protected method to register the sensor outputs to a connection
        which supports auto discover
        """
        for (conn, comm_conn) in comm.items():
            self.publishers[conn].register(comm_conn, None)

    def check_state(self):
        """Called to check the latest state of sensor and publish it. If not
        overridden it just calls publish_state().
        """
        self.publish_state()

    def publish_state(self):
        """Called to publish the current state to the publishers. The default
        implementation is a pass.
        """

    def _send(self, message, comm, output_name=None):
        """Sends message the the comm(unicators). Optionally specifie the output_name
        to set a output channel to publish to.

        Arguments:
        - message:     the message to publish as string or dict (generated from get_msg_from_values)
        - comm:        communication dictionary, with information where to publish
                       contains connection named dictionarys for each connection,
                       containing the connection related parameters
        - output_name: optional, the output channel to publish the message to,
                       defines the subdirectory in comm_conn to look for the return topic.
                       When defined the output_name must be present
                       in the sensor YAML configuration:
                       Connections:
                           <connection_name>:
                                <output_name>:
        """
        #accept regular messages directly
        if not isinstance(message, dict):
            msg = message

        for conn in comm.keys():
            #if message is a value_dict from get_msg_from_values, grab the current conn message
            #use list in default section if conn section is not present
            if isinstance(message, dict):
                msg = message.get(conn, message[DEFAULT_SECTION])

            self.publishers[conn].publish(msg, comm[conn], output_name)

    def cleanup(self):
        """Called when shutting down the sensor, give it a chance to clean up
        and release resources."""
