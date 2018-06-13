"""
   Copyright 2016 Richard Koshak / Lenny Shirley

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script:      bluetoothScanner.py
 Author:      Rich Koshak / Lenny Shirley <http://www.lennysh.com>
 Date:        February 11, 2016
 Purpose:     Scans for a Bluetooth device with a given address and publishes whether or not the device is present using RSSI figures, or lookup function.
Credit From:  https://github.com/blakeman399/Bluetooth-Proximity-Light/blob/master/https/github.com/blakeman399/Bluetooth-Proximity-Light.py
"""

import fcntl
import struct
import array
import sys
try:
    import bluetooth
    import bluetooth._bluetooth as bt
    bluezCheck = 1
except:
    bluezCheck = 0
try:
	from bluepy.btle import Scanner, DefaultDelegate
	bluepyCheck = 1
except:
	bluepyCheck = 0

debug = 0

class btSensor:
    """Represents a Bluetooth device"""

    def __init__(self, publisher, logger, params, sensors, actuators):
        """Finds whether the BT device is close and publishes its current state"""
        self.logger = logger
        self.publish = publisher
        self.address = params("Address")
        self.destination = params("Destination")
        self.logger.info("----------Configuring BluetoothSensor: Address = " + self.address + " Destination = " + self.destination)

        self.mode = params("Mode")

        if self.mode != "BTLE" and bluezCheck != 1:
            logger.error("Please install bluez for RSSI or LOOKUPi mode")
            raise ImportError("bluez missing")

        if self.mode != "RSSI" and self.mode != "LOOKUP" and self.mode != "BTLE":
            self.logger.error("\"%s\" is an unknown MODE, defaulting to RSSI" % (self.mode))
            self.mode = "RSSI"

        self.logger.info("---Running in \"" + self.mode + "\" mode")
        if self.mode == "RSSI":
            self.maxCnt = int(params("Max"))
            self.near = int(params("Near"))
            self.far = int(params("Far"))

	"""Support of Bluetooth LE scanning for BTLE Tags like the Gigaset G-Tag"""
	if self.mode == "BTLE":
            self.scanTimeout = int(params("ScanTimeout"))
            self.found = params("ON")
            self.missing = params("OFF")
            """Here we set default values if they are not set in config file"""
            if self.found == "":
                self.found = "ON"
            if self.missing == "":
                self.missing = "OFF"

            self.state = self.missing

        if self.mode != "BTLE":
            self.state = "OFF"

        self.poll = float(params("Poll"))

        # assume phone is initially far away
        self.far_count = 0
        self.near_count = 0
        self.rssi = None

        if self.mode =="BTLE" and bluepyCheck == 0:
            msg = "Please install bluepy for Bluetooth LE scanning or change ini file"
            print msg
            logger.error(msg)
            raise ImportError ("bluepy missing")
        else:
            self.publishState()

    def getPresence(self):
        """Detects whether the device is near by or not using lookup_name"""
        result = bluetooth.lookup_name(self.address, timeout=25)
        if(result != None):
            return "ON"
        else:
            return "OFF"

    def getTag(self):
        """Scans for BT LE devices and returns the choosen keywords"""
        self.count = 0
        scanner = Scanner().withDelegate(DefaultDelegate())
        devices = scanner.scan(self.scanTimeout)
        for dev in devices:
            if dev.addr == self.address.lower():
                self.count = 1
			
        if self.count > 0:
            self.count = 0
            return self.found
        else:
            return self.missing

    def getRSSI(self):
        """Detects whether the device is near by or not using RSSI"""
        addr = self.address

        # Open hci socket
        hci_sock = bt.hci_open_dev()
        hci_fd = hci_sock.fileno()

        # Connect to device (to whatever you like)
        bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        bt_sock.settimeout(10)
        result = bt_sock.connect_ex((addr, 1))	# PSM 1 - Service Discovery

        try:
            # Get ConnInfo
            reqstr = struct.pack("6sB17s", bt.str2ba(addr), bt.ACL_LINK, "\0" * 17)
            request = array.array("c", reqstr )
            handle = fcntl.ioctl(hci_fd, bt.HCIGETCONNINFO, request, 1)
            handle = struct.unpack("8xH14x", request.tostring())[0]

            # Get RSSI
            cmd_pkt=struct.pack('H', handle)
            rssi = bt.hci_send_req(hci_sock, bt.OGF_STATUS_PARAM,
                         bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4, cmd_pkt)
            rssi = struct.unpack('b', rssi[3])[0]

            # Close sockets
            bt_sock.close()
            hci_sock.close()

            return rssi

        except Exception, e:
            #self.logger.error("<Bluetooth> (getRSSI) %s" % (repr(e)))
            return None

    def checkState(self):
        """Detects and publishes any state change"""
        if self.mode == "RSSI":
            value = self.state
            self.rssi = self.getRSSI()

            #if debug:
            #if self.rssi == None:
            #    self.logger.info("Destination = " + self.destination + ", Current RSSI = None")
            #else:
            #    self.logger.info("Found! - Destination = " + self.destination + ", Current RSSI = " + str(self.rssi))

            if self.rssi == None:
                self.far_count += 1
                self.near_count -= 1
                if self.near_count < 0:
                    self.near_count = 0
                if self.far_count > self.maxCnt:
                    self.far_count = self.maxCnt
                #self.logger.info("Destination " + self.destination + " not found")
                #if self.far_count > 10:
                #    value = "OFF"
            elif self.rssi < -1:
                self.far_count -= 1
                self.near_count += 1
                if self.far_count < 0:
                    self.far_count = 0
                if self.near_count > self.maxCnt:
                    self.near_count = self.maxCnt
                #self.logger.info("Destination " + self.destination + " detected")
                #if self.near_count > 10:
                #    value = "ON"
            if self.near_count > self.far_count and self.near_count > self.near:
                value = "ON"
            elif self.far_count > self.near_count and self.far_count > self.far:
                value = "OFF"
            else:
                value = self.state
            #self.logger.info("Destination " + self.destination + " far count = " + str(self.far_count) + " near count " + str(self.near_count) + " RSSI = " + str(self.rssi))

        elif self.mode == "LOOKUP":
            value = self.getPresence()

	elif self.mode == "BTLE" and bluepyCheck == 1:
            value = self.getTag()

        else:
            msg = "Invalid 'mode' specified in 'bluetoothScanner.py' !"
            print msg
            self.logger.error(msg)
            return

        if value != self.state:
            self.state = value
            self.publishState()

    def publishState(self):
        """Publishes the current state"""
        for conn in self.publish:
            conn.publish(self.state, self.destination)
