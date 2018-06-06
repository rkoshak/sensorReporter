"""
   Copyright 2016 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script  execActuator
 Author: Rich Koshak
 Date:   April 19, 2016
 Purpose: Executes the configured command and publishes the result
"""

import os
import sys

if os.name == 'posix' and sys.version_info[0] < 3:
  import subprocess32 as subprocess
else:
  import subprocess
import subprocess32

class execActuator:
    """Represents an actuator connected to a command line script"""

    def __init__(self, connections, logger, params, sensors, actuators):
        """Sets the output and changes its state when it receives a command"""

        self.logger = logger

        self.command = params("Command")

        self.cmdTopic = params("CMDTopic")
        self.pubTopic = params("ResultTopic")
        self.connections = connections

        self.logger.info('----------Configuring execActuator: cmdTopic = {0}, pubTopic = {1}, command = {2}'.format(self.cmdTopic, self.pubTopic, self.command))
        
        for connection in self.connections:
            connection.register(self.cmdTopic, self.on_message)
    
    def publishImpl(self, output, topic):
        for connection in self.connections:
            connection.publish(output, topic)

    def on_message(self, client, userdata, msg):
        """Process a message"""
        self.logger.info('Received command on {0}: {1}'.format(self.cmdTopic, msg.payload))
        
        inArgs = msg.payload.split(' ')
        cmdArgs = []
        for arg in self.command.split(' '):
          if arg.find(';') == -1 or arg.find('|') == -1 or arg.find('//') == -1:
            cmdArgs.append(arg)
        for arg in inArgs:
          if arg != 'NA' and arg.find(';') == -1 and arg.find('|') == -1 and arg.find('//') == -1:
            cmdArgs.append(arg)

        self.logger.info('Executing command with the following arguments: {0}'.format(cmdArgs))
        try:
          output = subprocess.check_output(cmdArgs, shell=False, universal_newlines=True)
          self.logger.info('Command results to be published to {0}\n{1}'.format(self.pubTopic, output))
          self.publishImpl(output, self.pubTopic)
        except subprocess.CalledProcessError as e:
          self.logger.info('Command returned an error code: {0}\n{1}'.format(e.returncode, e.output))
          self.publishImpl('ERROR', self.pubTopic)
