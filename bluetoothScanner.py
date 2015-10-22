"""
 Script: bluetoothScanner.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Scans for a Bluetooth device with a given address and publishes 
   whether or not the device is present.
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import bluetooth
import paho.mqtt.client as mqtt

class btSensor:
    """Represents a Bluetooth device"""


    def __init__(self, address, topic, publish, logger, poll):
        """Finds whether the BT device is close and publishes its current state"""

        self.logger = logger
        self.logger.info("----------Configuring BluetoothSensor: Address = " + address + " Topic = " + topic)
        self.address = address
        self.state = self.getPresence()
        self.topic = topic
        self.publish = publish
        self.poll = poll

        self.publishState()

    def getPresence(self):
        """Detects whether the device is near by or not"""
        result = bluetooth.lookup_name(self.address, timeout=25)
        if(result != None):
            return "ON"
        else:
            return "OFF"

    def checkState(self):
        """Detects and publishes any state change"""

        value = self.getPresence()
        if(value != self.state):
            self.state = value
            self.publishState()

    def publishState(self):
        """Publishes the current state"""

        self.publish(self.topic, self.state)
