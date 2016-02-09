"""
 Script:      bluetoothRSSIScanner.py
 Author:      Lenny Shirley <http://www.lennysh.com>
 Date:        February 9, 2016
 Purpose:     Scans for a Bluetooth device with a given address and publishes 
   whether or not the device is present using RSSI figures.
Credit From:  https://github.com/blakeman399/Bluetooth-Proximity-Light/blob/master/https/github.com/blakeman399/Bluetooth-Proximity-Light.py
"""

import fcntl
import struct
import array
import bluetooth
import bluetooth._bluetooth as bt

debug = 0

class btSensor:
    """Represents a Bluetooth device"""

    def __init__(self, address, topic, publish, logger, poll):
        """Finds whether the BT device is close and publishes its current state"""

        self.logger = logger
        self.logger.info("----------Configuring BluetoothSensor: Address = " + address + " Topic = " + topic)
        self.address = address
        self.state = "OFF"
        self.topic = topic
        self.publish = publish
        self.poll = poll

        # assume phone is initially far away
        self.far = True
        self.far_count = 0
        self.near_count = 0
        self.rssi = None
        self.prev1rssi = None
        self.prev2rssi = None

        self.publishState()

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
            return None

    def checkState(self):
        """Detects and publishes any state change"""

        value = self.state
        self.rssi = self.getRSSI()
		
        if debug:
            print "Topic = %s, Current RSSI = %s, Previous RSSI = %s, RSSI before Previous = %s" % (self.topic, self.rssi, self.prev1rssi, self.prev2rssi)

        if self.rssi == self.prev1rssi == self.prev2rssi == None:
            self.far_count += 1
            self.near_count = 0
            if self.far_count > 10:
                value = "OFF"
        else:
            self.far_count = 0
            self.near_count += 1
            if self.near_count > 10:
                value = "ON"

        if value != self.state:
            self.state = value
            self.publishState()

        self.prev2rssi = self.prev1rssi
        self.prev1rssi = self.rssi

    def publishState(self):
        """Publishes the current state"""

        self.publish(self.state, self.topic)
