# Copyright 2021 Alexander Behring
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
"""Simple script to test connection to the pafal smart meter.
"""
from em_connections import Pafal20ec3grConnector
import argparse

_SERIAL_DEVICE_DEFAULT = "/dev/ttyUSB0"


parser = argparse.ArgumentParser(description='Perform a test read to the pafal device.')

parser.add_argument( '--port',
    nargs       = 1,
    required    = False,
    help        = 'The device file to use for accessing the serial connection to Pafal '
        '(defaults to {deflt})'.format(deflt = _SERIAL_DEVICE_DEFAULT)
)

args = parser.parse_args()

myPort = _SERIAL_DEVICE_DEFAULT
if args.port:
  myPort = args.port[0]


print("Setting up class ...")
serdev = Pafal20ec3grConnector( devicePort=myPort )

print("Requesting data ...")
result = serdev.readData( {
    "0.0.0": [False],
    "0.2.0": [False],
    "1.8.0*00": [True],
    "2.8.0*00": [True]
} )

print("Result:")
print("Meter number: " +    result.get("0.0.0", "<could not be acquired>"))
print("Meter firmware: " +  result.get("0.2.0", "<could not be acquired>"))
print("Total import: " +    str(result.get("1.8.0*00", "<could not be acquired>")))
print("Total export: " +    str(result.get("2.8.0*00", "<could not be acquired>")))


print("Closing connection")
serdev.close()

print("Finished")