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
"""Contains sensors that look to see if given BT devices are present. Does not
look for BTLE devices.

Classes:
    -SimpleBtSensor: Looks for a device by address and if it finds it publishes
    ON.
    - BtRssiSensor: Looks for a device by address and it it sees it enough times
    publishes ON.
"""
import struct
import traceback
import bluetooth
import bluetooth._bluetooth as bt
from core.sensor import Sensor
from core.utils import get_sequential_params

class SimpleBtSensor(Sensor):
    """Implements a simple scanner that looks for the name of a BT devices given
    their MAC addresses.
    """

    def __init__(self, publishers, params):
        """Parses the parameters and prepares to scan for the configured devices.
        Params:
            - Poll: must be greater than 25
            - AddressX: sequential list of MAC addresses to look for
            - DestinationX: sequential list of destinations to publish ON/OFF to
            when the corresponding Address is found or not. There must be the
            same numer of Address and Destiantion fields.
        Raises:
            - NoOptionError: when a required parameter doesn't exist
            - ValueError: when the list of Addresses and Destinations don't
            match up or Poll is too small.
        """
        super().__init__(publishers, params)

        addresses = get_sequential_params(params, "Address")
        destinations = get_sequential_params(params, "Destination")
        laststates = [None] * len(addresses)
        if len(addresses) != len(destinations):
            raise ValueError("List of addresses and destinations are not the same length")
        self.devices = dict(zip(addresses, destinations))
        self.states = dict(zip(addresses, laststates))

        if self.poll <= 25:
            raise ValueError("Poll must be more than 25")

        self.log.info("Configured simple BT sensor")

    def check_state(self):
        """Loops through the devices and tries to see if they are reachable over
        Bluetooth.
        """
        for address in self.devices:
            result = bluetooth.lookup_name(address, timeout=25)
            self.log.debug("Scanned for %s, result = %s", address, result)
            value = "OFF" if result is None else "ON"
            if value != self.states[address]:
                self.states[address] = value
                self._send(value, self.devices[address])

    def publish_state(self):
        """Publishes the last set of states for each device."""
        for address in self.devices:
            self._send(self.states[address], self.devices[address])

class BtRssiSensor(Sensor):
    """Initiates an inquiry and then reads the response packets and pulls the
    RSSI. If the RSSI is negative it's near count is incremented and far count
    is decremented. When it is not seen, the near count is decremented and far
    count is incremented. When the near count is greater than the far count and
    greater than the "Near" parameter ON is published. When the far count is
    greater than the near count and greater than the "Far" parameter OFF is
    published.
    """

    def __init__(self, publishers, params):
        """Parses the parameters in preparation to scanning.
        Params:
            - Poll: must be greater than 10
            - Address: BT MAC address to look for
            - Destination: where to publish the results
            - Max: maximum number to count up to for both the near and far counts
            - Near: number for the near count above which ON will be published
            - Far: number for the far count above which OFF will be published
        Raises:
            - NoOptionError: when a required parameter doesn't exist
            - ValueError: when Poll is too small.
        """
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

    def read_inquiry_mode(self, sock):
        """Cribbed from the PyBluez inquiry-with-rssi.py example"""
        # Save the current filter
        old_filter = sock.getsockopt(bt.SOL_HCI, bt.HCI_FILTER, 14)

        # Setup the filter to receive only events related to the
        # read_inquirey_mode command.
        flt = bt.hci_filter_new()
        opcode = bt.cmd_opcode_pack(bt.OGF_HOST_CTL, bt.OCF_READ_INQUIRY_MODE)
        bt.hci_filter_set_ptype(flt, bt.HCI_EVENT_PKT)
        bt.hci_filter_set_event(flt, bt.EVT_CMD_COMPLETE)
        bt.hci_filter_set_opcode(flt, opcode)
        sock.setsockopt(bt.SOL_HCI, bt.HCI_FILTER, flt)

        # First read the current inquirey mode.
        bt.hci_send_cmd(sock, bt.OGF_HOST_CTL, bt.OCF_READ_INQUIRY_MODE)

        pkt = sock.recv(255)
        status, mode = struct.unpack("xxxxxxBB", pkt)

        # Restore the old filter
        sock.setsockopt(bt.SOL_HCI, bt.HCI_FILTER, old_filter)

        return mode

    def write_inquiry_mode(self, sock, mode):
        """Cribbed from the PyBluez inquiry-with-rssi.py example"""
        old_filter = sock.getsockopt(bt.SOL_HCI, bt.HCI_FILTER, 14)

        # Setup socket filter to receive only events related to the
        # write_inquire_mode command
        flt = bt.hci_filter_new()
        opcode = bt.cmd_opcode_pack(bt.OGF_HOST_CTL, bt.OCF_WRITE_INQUIRY_MODE)
        bt.hci_filter_set_ptype(flt, bt.HCI_EVENT_PKT)
        bt.hci_filter_set_event(flt, bt.EVT_CMD_COMPLETE)
        bt.hci_filter_set_opcode(flt, opcode)
        sock.setsockopt(bt.SOL_HCI, bt.HCI_FILTER, flt)

        # Send the command
        bt.hci_send_cmd(sock, bt.OGF_HOST_CTL, bt.OCF_WRITE_INQUIRY_MODE,
                        struct.pack("B", mode))

        pkt = sock.recv(255)
        status = struct.unpack("xxxxxxB", pkt)[0]

        # Restore the old filter
        sock.setsockopt(bt.SOL_HCI, bt.HCI_FILTER, old_filter)

        return 0 if status else -1

    def device_inquiry_with_rssi(self, sock):
        """Cribbed from the PyBluez inquiry-with-rssi.py example. Returns a list
        of tuples with BT device addresses and the RSSI value.
        """
        # save the old filter
        old_filter = sock.getsockopt(bt.SOL_HCI, bt.HCI_FILTER, 14)

        # Perform a device inquiry on bluetooth device. The inquiry should last
        # 8 * 1.28 = 10.24 seconds before the inquiry is performed, bluez should
        # flush it's cache of previously discovered devices.
        flt = bt.hci_filter_new()
        bt.hci_filter_all_events(flt)
        bt.hci_filter_set_ptype(flt, bt.HCI_EVENT_PKT)
        sock.setsockopt(bt.SOL_HCI, bt.HCI_FILTER, flt)

        duration = 4
        max_responses = 255
        cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
        bt.hci_send_cmd(sock, bt.OGF_LINK_CTL, bt.OCF_INQUIRY, cmd_pkt)

        results = []

        while True:
            pkt = sock.recv(255)
            ptype, event, plen = struct.unpack("BBB", pkt[:3])
            if event == bt.EVT_INQUIRY_RESULT_WITH_RSSI:
                pkt = pkt[3:]
                nrsp = bluetooth.get_byte(pkt[0])
                for i in range(nrsp):
                    addr = bt.ba2str(pkt[1+6*i:1+6*i+6])
                    rssi = bluetooth.byte_to_signed_int(bluetooth.get_byte(pkt[1 + 13 * nrsp + i]))
                    results.append((addr, rssi))
            elif event == bt.EVT_INQUIRY_COMPLETE:
                break
            elif event == bt.EVT_CMD_STATUS:
                status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
                if status:
                    self.log.warning("Something went wrong")
                    break
            elif event == bt.EVT_INQUIRY_RESULT:
                pkt = pkt[3:]
                nrsp = bluetooth.get_byte(pkt[0])
                for i in range(nrsp):
                    addr = bt.ba2str(pkt[1+6*1:1+6*i+6])
                    results.append((addr, -1))
            else:
                self.log.debug("Unrecognized packet type")

        sock.setsockopt(bt.SOL_HCI, bt.HCI_FILTER, old_filter)
        return results

    def get_rssi(self):
        """Sets up the BT device and collects all the RSSI values it can for a
        few seconds. Looks through the results and for the device we care about
        return the first RSSI value we saw.
        """
        # Open the HCI socket.
        try:
            sock = bt.hci_open_dev(0)
        except Exception as exc:
            self.log.error("Error accessing bluetooth device: %s\n%s", exc,
                           traceback.format_exc())
            return None

        # Get the mode.
        try:
            mode = self.read_inquiry_mode(sock)
        except Exception as exc:
            self.log.error("Error reading inquiry mode: %s", exc)
            sock.close()
            return None

        # Change the mode.
        if mode != 1:
            try:
                result = self.write_inquiry_mode(sock, 1)
            except Exception as exc:
                self.log.error("Error writing inquiry mode: %s", exc)
                sock.close()
                return None
            if result:
                self.log.error("Error while setting inquiry mode")
                sock.close()
                return None

        # Collect rssi packets.
        results = self.device_inquiry_with_rssi(sock)
        sock.close()

        # Look through the results for the device we care about.
        self.log.debug("Results = %s, looking for results for %s", results, self.address.upper())
        found = [rssi for rssi in results if rssi[0] == self.address.upper()]

        # Return the first one.
        return found[0][1] if found else None

    def check_state(self):
        """Gets the RSSI for the device we care about. If it's present (i.e.
        RSSI < -1) we increment the near count and decrement the far count,
        doing opposite when it's not present. When the counts get high enough
        ON or OFF is published.
        """
        value = self.state
        rssi = self.get_rssi()
        self.log.debug("Device %s has RSSI of %s", self.address.upper(), rssi)

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
        """Publishes the last state."""
        self._send(self.state, self.destination)
