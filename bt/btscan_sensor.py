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
import array
import fcntl
import struct
import bluetooth
import bluetooth._bluetooth as bt
from core.sensor import Sensor

class SimpleBtSensor(Sensor):

    def __init__(self, publishers, params):
        super().__init__(publishers, params)

        self.address = params("Address")
        self.destination = params("Destination")
        if self.poll <= 25:
            raise ValueError("Poll must be less than 25")

        self.log.info("Configured simple BT sensor for %s, publishing to %s", self.address, self.destination)
        self.state  = None

    def check_state(self):
        result = bluetooth.lookup_name(self.address, timeout=25)
        self.log.debug("Scanned for %s, result = %s", self.address, result)
        value = "OFF" if result is None else "ON"
        if value != self.state:
            self.state = value
            self.publish_state()

    def publish_state(self):
        self._send(self.state, self.destination)

class BtRssiSensor(Sensor):

    def __init__(self, publishers, params):
        super().__init__(publishers, params)

        self.address = params("Address")
        self.destination = params("Destination")
        self.max_count = int(params("Max"))
        self.max_near = int(params("Near"))
        self.max_far = int(params("Far"))

        # Default the state to OFF/far away.
        self.state = "OFF"
        self.near_count = 0
        self.far_count = 0

        if self.poll <= 10:
            raise ValueError("Poll must be greater than 10 seconds.")

    def get_rssi(self):
        # Open the HCI socket.
        self.log.debug("Opening the socket")
        hci_sock = bt.hci_open_dev()
        hci_fd = hci_sock.fileno()

        # Connect to the BT transceiver.
        bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        bt_sock.settimeout(10)
        result = bt_sock.connect_ex((self.address, 1)) # PSM 1 = Service Discovery

        rssi = None
        try:
            # Get ConnInfo
            self.log.debug("Getting request string")
            reqstr = struct.pack("6sB17s", bt.str2ba(self.address), bt.ACL_LINK,
                                 b"\0" * 17)
            self.log.debug("building the request array")
            request = array.array("b", reqstr)
            self.log.debug("parsing the handle")
            handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
            self.log.debug("Unpacking the handle")
            handle = struct.unpack("8xH14x", request.tostring())[0]

            # Get RSSI
            self.log.debug("Packing the handle")
            cmd_pkt = struct.pack('H', handle)
            self.log.debug("Extracting the rssi")
            rssi = bt.hci_send_req(hci_sock, bt.OGF_STATUS_PARAM,
                                   bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4,
                                   cmd_pkt)
            self.log.debug("Getting the final rssi value")
            rssi = struct.unpack('b', rssi[3])[0]

        except Exception as exc:
            self.log.warning("Error scanning for %s: %s", self.address, exc)
            rssi = None
        finally:
            # Close sockets
            self.log.debug("Closing the socket")
            bt_sock.close()
            hci_sock.close()
            return rssi

    def check_state(self):
        value = self.state
        rssi = self.get_rssi()

        # Update the near/far counts
        def update_count(amt, cnt):
            rval = cnt + amt
            if rval < 0:
                rval = 0
            elif rval > self.max_count:
                rval = self.max_count
            return rval

        if rssi is None:
            self.far_count = update_count(1, self.far_count)
            self.near_count = update_count(-1, self.near_count)
        elif rssi < -1:
            self.far_count = update_count(-1, self.far_count)
            self.near_count = update_count(1, self.near_count)

        if self.near_count > self.far_count and self.near_count > self.max_near:
            value = "ON"
        elif self.far_count > self.near_count and self.far_count > self.max_far:
            value = "OFF"

        if value != self.state:
            self.state = value
            self.publish_state()

    def publish_state(self):
       self._send(self.state, self.destination)
