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

""" Contains an ExecActuator, an Actuator that executes a command when receiving
    a message.

    Classes: ExecActuator
"""

import subprocess
from typing import Any, Dict, TYPE_CHECKING
import yaml
from core.actuator import Actuator
from core import utils
if TYPE_CHECKING:
    # Fix circular imports needed for the type checker
    from core import connection

class ExecActuator(Actuator):
    """ Actuator that calls a configured command line script using the passed in
        message as arguments. The result of the command is published to another
        destination.
    """

    def __init__(self,
                 connections:Dict[str, 'connection.Connection'],
                 dev_cfg:Dict[str, Any]) -> None:
        """ Sets up the actuator to call the command scripts. Expects the
            following parameters.
            - "Command": the command line to execute
            - "Connections": holds the dictionary's with the configured connections
               for each actuator. Will subscribe to the specified Topic, messages to this topic are
               turned into command line arguments; if "NA" it's treated as no arguments.
               The command result is published to the specified return topic;
               ERROR is published if the command returned a non-zero return code.
            - "Timeout": The number of seconds to let the command run before timing out.
        """
        super().__init__(connections, dev_cfg)

        self.command = dev_cfg["Command"]
        self.timeout = int(dev_cfg["Timeout"])

        self.log.info("Configuring Exec Actuator: %s, Command = %s",
                      self.name, self.command)
        self.log.debug("%s has following configured connections: \n%s",
                       self.name, yaml.dump(self.comm))

        utils.configure_device_channel(self.comm, is_output=False,
                                       name="terminal command input")
        utils.configure_device_channel(self.comm, is_output=True,
                                       name="terminal command result")
        #the actuator gets registered twice, at core-actuator and here
        # currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self,
                   msg:str) -> None:
        """ When a message is received on the "Command" destination this method
            is called. Executes the command and publishes the result. Any argument
            that contains ';', '|', or '//' are ignored.
        """
        self.log.info("%s received command: %s", self.name, msg)

        cmd_args = [arg for arg in self.command.split(' ') if utils.issafe(arg)]

        if msg and msg != "NA":
            for arg in [arg for arg in msg.split(' ') if utils.issafe(arg)]:
                cmd_args.append(arg)

        self.log.info("%s executed command with the following arguments: %s", self.name, cmd_args)

        try:
            output = subprocess.check_output(cmd_args, shell=False,
                                             universal_newlines=True,
                                             timeout=self.timeout).rstrip()
            self.log.info("%s command result: %s",
                          self.name, output)
            self._publish(output, self.comm)
        except subprocess.CalledProcessError as ex:
            self.log.error("Command returned an error code: %s\n%s",
                           ex.returncode, ex.output)
            self._publish("ERROR", self.comm)
        except subprocess.TimeoutExpired:
            self.log.error("Command took longer than 10 seconds.")
            self._publish("ERROR", self.comm)
