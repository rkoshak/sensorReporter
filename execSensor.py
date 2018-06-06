"""
   Copyright 2018 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: execSensor.py
 Author: Rich Koshak
 Date:   June 6, 2018
 Purpose: Periodically calls a script/program and publiahes the result
"""

import sys
import time
import os

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

class execSensor:
    """Periodically calls a script/program and publishes the result"""

    def __init__(self, publishers, logger, params, sensors, actuators):
        """Sets the script to call and destination for the results"""

        self.logger = logger
        self.publishers = publishers
        self.poll = float(params("Poll"))
        self.script = params("Script")
        self.dest = params("Destination")
        self.startTime = time.time()
        
        """Parse out the script and arguments, ignoring dangerous characters"""
        self.cmdArgs = []
        for arg in self.script.split(' '):
            if arg.find(';') == -1 or arg.find('|') == -1 or arg.find('//') == -1:
                self.cmdArgs.append(arg)

        self.results = ""

        self.logger.info('----------Configuring execSensor call script {0} and destination {1} with interval {2}'.format(self.script, self.dest, self.poll))
        self.checkState

    def checkState(self):
        """calls the script and publishes the result"""

        self.logger.info('Executing script with the following arguments: {0}'.format(self.cmdArgs))
        try:
            self.results = subprocess.check_output(self.cmdArgs, shell=False, universal_newlines=True)
            self.logger.info('Command results to be published to {0}\n{1}'.format(self.dest, self.results))
        except subprocess.CalledProcessError as e:
            self.logger.warn('Command returned an error code: {0}\n{1}'.format(e.returncode, e.output))
            self.results = 'Error'

        self.publishState()

    def publishState(self):
        """Publishes the most recent result from the script"""
        for conn in self.publishers:
            conn.publish(self.results, self.dest)

    def cleanup(self):
        """Does nothing"""
