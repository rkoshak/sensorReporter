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
"""Module implementing the reading out of values for `read_meter_values.py`.

Classes:
    - Pafal20ec3grConnector (supports Pafal 20ec3gr)
"""

# Technical details, see for example:
# * http://wiki.volkszaehler.org/hardware/channels/meters/power/edl-ehz/pafal-20ec3gr
# * https://forum.fhem.de/index.php?topic=105726.0
# * http://manuals.lian98.biz/doc.de/html/g_iec62056_struct.htm#IEC%2062056-21%20:%20Telegramm%20Struktur


import serial
import time
import logging
from datetime import datetime

_SERIAL_DEVICE = "/dev/ttyUSB0"

# Message sent to init request to Pafal
_INIT_REQUEST = b"/?!\r\n"

# Expected response on init message:
# /PAF
# 5	-- 9.6k , Mode C
# EC3gr00006	- ID
# \r\n
_INIT_RESPONSE = "/PAF5EC3gr00006"

# Message sent after Init to request data
# With 300 Baud: b"\x06000\r\n"
# With 9600 Baud: b"\x06050\r\n"  -  but does not seem to work :(
_READ_DATA_REQUEST = b"\x06000\r\n"
_READ_RETURN_SPEED = 300

# Expected message after data request
# <Startsequence>
# 0.0.0(71786316)		- Meter number
# 0.0.1(PAF)			- Owner bumber
# F.F(00)				- ???
# 0.2.0(1.27)			- Firmware
# 1.8.0*00(048162.13)	-	energy import ("Bezug")
# 2.8.0*00(035411.79) -	energy export ("Lieferung")

# 0.2.2(:::::G11)!	- "Schaltuhrenprogramm" + Termination character
# q		- Block check
_DATA_EOT_SIGNAL = "!"
_DATA_STARTSEQUENCE = b"\x02"


class Pafal20ec3grConnector(object):
    """Class to interface with the Pafal 20ec3gr via a serial connection.
    It supports a minimal subset of a iec62056 communication, which is tailored for the supported Pafal 20ec3gr device.
    The OBIS system is supported for extracting out the values from the response."""

    def __init__(self, devicePort = _SERIAL_DEVICE, logger = None):
        """Creates the connector class.
        Parameters:
        * devicePort: the device file to access for serial connection (e.g. /dev/ttyUSB0)
        * logger: the logger to use, defaults to creating its own

        Note that this call does not invoke a connection to the serial device."""
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.serialDevice = None
        self.devicePort = devicePort

    def _sendRequest(self, request):
        """Sends an output to the device"""
        self.serialDevice.flushInput()		#discard anything that is there
        self.serialDevice.write(request)

    def _readResponse( self, readpause = 0.1, eotSignal = None, extTimeout = 8, maxlen = 255 ):
        """Read a response from Pafal. If eotSignal == None, just read once until timeout / EOL.
        If eotSignal != None, read until eotSignal or extTimeout."""

        # Start with sleep, as we likely just sent the request...
        time.sleep(readpause)

        # Read - may take more than time out...
        response = ""
        startTime = datetime.now()
        while True:
            readBytes = self.serialDevice.read(size = maxlen)
            if eotSignal is None:
                return None if not readBytes else readBytes.decode()
            if readBytes:
                response += readBytes.decode()
                if eotSignal in readBytes.decode():
                    return response
            if (datetime.now() - startTime).seconds > extTimeout:
                self.logger.error("Time out reading until eot. Got: '{resp}'.".format(
                    resp = "<NONE>" if not response else response.replace("\r","").replace("\n","")
                ))
                return None if not response else response
            # Short break before next cycle
            time.sleep(readpause)

    def _setupDevice(self):
        """Re (inits) the connection to the device."""
        if self.serialDevice:
            self.close()

        self.serialDevice = serial.Serial(
            port = self.devicePort,
            bytesize=serial.SEVENBITS,
            baudrate=300,
            parity = serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout = 1)
        self.logger.debug("Opened port '{port}' for accessing Pafal data".format(port = self.devicePort))

    def _splitData(self, dataString):
        """Splits data from OBIS ID.

        E.g. "1.8.0*00(048162.13)" is returned as ["1.8.0*00", "048162.13"].
        """
        if not dataString:
            return [None, None]

        leftB = dataString.find("(")
        rightB = dataString.find(")")
        if leftB == -1 or rightB ==-1 or leftB>rightB:
            self.logger.warn("Cannot extract data from line '{line}' - brackets in wrong positions or not there.".format(
                line = dataString
            ))
            return [None, None]

        return [ dataString[:leftB], dataString[leftB+1:rightB] ]

    def readData(self, requestedIDs):
        """Reads the actual data from the device, returns a dict with the requested data.
        Shall not be called with higher frequency than 1 call / 20 seconds, as reading out with 300 Baud is ....slow....

        No previous intialization required - this method takes care of connecting to the device. Connection is left open.

        Parameters:
        * requestedIDs: a dict containing the desired OBIS IDs yielding a config array, e.g. { "1.8.0*00": [True] }.
          The config array contains:
          * a boolean whether conversion to float shall be performed

        Returns a dict with desired OBIS IDs yielding their values.

        Note: Not thread-safe. Blocking. If a handled error occurs, an empty dict is handed back. IO errors are not handled.
        """
        # Default return
        results = {}

        if self.serialDevice is None or not self.serialDevice.isOpen():
            self._setupDevice()

        # Perform initial read and check response
        self.serialDevice.baudrate = 300
        self._sendRequest(_INIT_REQUEST)
        response = self._readResponse()
        if response is None or (not response.replace("\r","").replace("\n","") == _INIT_RESPONSE):
            self.logger.error("Pafal did not send expected response on init. Got: '{resp}'.".format(
                resp = "<NONE>" if not response else response.replace("\r","").replace("\n","")
                ))
            return results

        # Perform data request
        self._sendRequest(_READ_DATA_REQUEST)
        self.serialDevice.baudrate = _READ_RETURN_SPEED
        response = self._readResponse( eotSignal = _DATA_EOT_SIGNAL, extTimeout = 10 )
        if not response or len(response) < 10:
            self.logger.error("Pafal response too small (<10 chars). Got: '{resp}'.".format(
                resp = "<NONE>" if not response else response.replace("\r","").replace("\n","")
                ))
            return results

        # Expect start seq at start which must be removed
        if not response[:len(_DATA_STARTSEQUENCE)] == _DATA_STARTSEQUENCE.decode():
            self.logger.error("Pafal did not respond with expected startsequence '{sseq}'. Got: '{sgot}'.".format(
                ssequ = ":".join("{:02x}".format(ord(c)) for c in _DATA_STARTSEQUENCE),
                sgot = ":".join("{:02x}".format(ord(c)) for c in response[:len(_DATA_STARTSEQUENCE)+2])
                ))
            return results
        else:
            response = response[len(_DATA_STARTSEQUENCE):]

        # Split up lines an process contents
        datalines = response.split("\n")
        if len(datalines) != 9:
            self.logger.error("Pafal did not respond with 9 lines of data. Got: '{resp}'.".format(resp = "**".join(datalines)))
            return results

        # Extract the wanted data parts
        for line in datalines:
            if len(line) < 4:
                # Likely check line, just skip
                continue
            idString, valString = self._splitData( line.replace("\n","").replace("\r","") )
            if (not idString is None) and (idString in requestedIDs.keys()):
                cfg = requestedIDs[idString]
                if cfg[0]:    # True --> asFloat
                    try:
                        val = float( valString )
                    except:
                        val = None
                        self.logger.warn("Response from Pafal was expected to be a float, but cannot be converted to such (response: '{re}').".format(
                            re = str(valString)
                        ))
                else:
                    val = valString
                results[idString] = val

        missingIDs = []
        for i in requestedIDs.keys():
            if not i in results.keys():
                missingIDs.append(i)

        if len(missingIDs)>0:
            self.logger.warn("Less data lines extracted from response than expected. Missing: {misses}".format(
                misses = ",".join(missingIDs)
            ))
        self.logger.debug("Returned {c} requested data chunks".format(c=len(results)))
        return results

    def close(self):
        """Closes the connection to the serial device (if it is open)."""
        if self.serialDevice:
            self.serialDevice.close()
            self.logger.debug("Closed serial port for accessing Pafal data.")
        else:
            self.logger.debug("No port to close.")
        self.serialDevice = None