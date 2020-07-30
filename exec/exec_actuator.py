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
from core.actuator import Actuator
import subprocess

class ExecActuator(Actuator):
    """Actuator that calls a configred command line script using the passed in
    message as arguments. The result of the command is published to another
    destination.
    """

    def __init__(self, connections, log, params):
        """Sets up the actuator to call the command scripts. Expects the
        following parameters.
        - "Command": the command line to execute
        - "Topic": the destination subscribed to, messages to this topic are
        turned into command line arguments; if "NA" it's treated as no arguments.
        - "ResultTopic": the destination to publish the output from the command;
        ERROR is published if the command returned a non-zero return code.
        """
        super().__init__(connections, log, params)

        self.command = params("Command")
        self.command_topic = params("Topic")
        self.result_topic = params("ResultTopic")

        self.log.info("Configuring Exec Actuator: Command Topic = {}, Result "
                      "Topic = {}, Command = {}"
                      .format(self.command_topic, self.result_topic, self.command))

    def on_message(self, client, userdata, msg):
        """When a message is received on the "Command" destination this method
        is called. Executes the command and publishes the result. Any argument
        that contains ';', '|', or '//' are ignored.
        """
        self.log("Receives command on {}: {}"
                 .format(self.command_topic, msg.payload))

        cmd_args = [arg for arg in self.command.split(' ')
                    if arg.find(';') == -1 and arg.find('|') == -1 and arg.find('//') == -1]

        [cmd_args.append(arg) for arg in msg.payload.split(' ')
         if arg != 'NA' and arg.find(';') == -1 and arg.find('|') == -1 and arg.find('//') == -1]

        self.log.info("Executing command withe the following arguments: {}"
                      .format(cmd_args))

        try:
            output = subprocess.check_output(cmd_args, shell=False,
                                             universal_newlines=True,
                                             timeout=10)
            self.log.info("Command results to be published to {}\n{}"
                          .format(self.result_topic, output))
            self._publish(output, self.result_topic)
        except subprocess.CallProcessError as e:
            self.log.error("Command returned and error code: {}\n{}"
                           .format(e.returncode, e.output))
            self._publish("ERROR", self.result_topic)
        except subprocess.TimoutExpired as e:
            self.log.error("Command took longer than 10 seconds.")
            self._publish("ERROR", self.result_topic)
