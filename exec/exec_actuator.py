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

"""Contains an ExecActuator, an Actuator that executes a command when receiving
a message.

Classes: ExecActuator
"""

import subprocess
from core.actuator import Actuator
from core.utils import issafe

class ExecActuator(Actuator):
    """Actuator that calls a configred command line script using the passed in
    message as arguments. The result of the command is published to another
    destination.
    """

    def __init__(self, connections, params):
        """Sets up the actuator to call the command scripts. Expects the
        following parameters.
        - "Command": the command line to execute
        - "CommandSrc": the destination subscribed to, messages to this topic are
        turned into command line arguments; if "NA" it's treated as no arguments.
        - "ResultsDest": the destination to publish the output from the command;
        ERROR is published if the command returned a non-zero return code.
        - "Timeout": The number of seconds to let the command run before timing
        out.
        """
        super().__init__(connections, params)

        self.command = params("Command")
        self.timeout = int(params("Timeout"))

        self.log.info("Configuring Exec Actuator: Command Topic = %s, Result "
                      "Topic = %s, Command = %s", self.cmd_src, self.destination,
                      self.command)

    def on_message(self, msg):
        """When a message is received on the "Command" destination this method
        is called. Executes the command and publishes the result. Any argument
        that contains ';', '|', or '//' are ignored.
        """
        self.log.info("Received command on %s: %s", self.cmd_src, msg)

        cmd_args = [arg for arg in self.command.split(' ') if issafe(arg)]

        if msg and msg != "NA":
            for arg in [arg for arg in msg.split(' ') if issafe(arg)]:
                cmd_args.append(arg)

        self.log.info("Executing command with the following arguments: %s", cmd_args)

        try:
            output = subprocess.check_output(cmd_args, shell=False,
                                             universal_newlines=True,
                                             timeout=self.timeout).rstrip()
            self.log.info("Command results to be published to %s\n%s",
                          self.destination, output)
            self._publish(output, self.destination)
        except subprocess.CalledProcessError as ex:
            self.log.error("Command returned an error code: %s\n%s",
                           ex.returncode, ex.output)
            self._publish("ERROR", self.destination)
        except subprocess.TimeoutExpired:
            self.log.error("Command took longer than 10 seconds.")
            self._publish("ERROR", self.destination)
