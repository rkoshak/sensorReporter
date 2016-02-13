"""
 Script:      bluetoothScanner.py
 Author:      Rich Koshak / Lenny Shirley <http://www.lennysh.com>
 Date:        February 11, 2016
 Purpose:     Scans for a Bluetooth device with a given address and publishes whether or not the device is present using RSSI figures, or lookup function.
Credit From:  https://github.com/blakeman399/Bluetooth-Proximity-Light/blob/master/https/github.com/blakeman399/Bluetooth-Proximity-Light.py
"""

import fcntl
import struct
import array
import bluetooth
import bluetooth._bluetooth as bt

debug = 0

"""Either use 'RSSI' mode, or 'LOOKUP' mode.  RSSI is more reliable."""
mode = "RSSI"

class btSensor:
    """Represents a Bluetooth device"""

    def __init__(self, address, destination, publish, logger, poll):
        """Finds whether the BT device is close and publishes its current state"""

        self.logger = logger
        self.logger.info("----------Configuring BluetoothSensor: Address = " + address + " Destination = " + destination)
        self.address = address
        self.state = "OFF"
        self.destination = destination
        self.publish = publish
        self.poll = poll

        # assume phone is initially far away
        self.far = True
        self.far_count = 0
        self.near_count = 0
        self.rssi = None

        self.publishState()

    def getPresence(self):
        """Detects whether the device is near by or not"""
        result = bluetooth.lookup_name(self.address, timeout=25)
        if(result != None):
            return "ON"
        else:
            return "OFF"

    def getRSSI(self):
        """Detects whether the device is near by or not"""
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

        if mode == "RSSI":
            value = self.state
            self.rssi = self.getRSSI()

            if debug:
                print "Destination = %s, Current RSSI = %s" % (self.destination, self.rssi)

            if self.rssi == None:
                self.far_count += 1
                self.near_count = 0
                if self.far_count > 10:
                    value = "OFF"
            elif self.rssi < 0:
                self.far_count = 0
                self.near_count += 1
                if self.near_count > 10:
                    value = "ON"
        elif mode == "LOOKUP":
            value = self.getPresence()
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

        self.publish(self.state, self.destination)
