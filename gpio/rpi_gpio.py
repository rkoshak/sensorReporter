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
"""Contains RPI GPIO sensors, actuators, and connections.

Classes:
    - RpiGpioSensor: Reports on the state of a GPIO Pin.
    - RpiGpioActuator: Sets a pin to HIGH or LOW on command.
"""
from time import sleep
from configparser import NoOptionError
import RPi.GPIO as GPIO
from core.sensor import Sensor
from core.actuator import Actuator
from core.utils import parse_values
from distutils.util import strtobool 
import datetime

# Set to use BCM numbering.
GPIO.setmode(GPIO.BCM)

class RpiGpioSensor(Sensor):
    """Publishes the current state of a configured GPIO pin."""

    def __init__(self, publishers, params):
        """Initializes the connection to the GPIO pin and if "EventDetection"
        if defined and valid, will subscibe fo events. If missing, than it
        requires the "Poll" parameter be defined and > 0. By default it will
        publish CLOSED/OPEN for 0/1 which can be overridden by the "Values" which
        should be a comma separated list of two paameters, the first one is
        CLOSED and second one is OPEN.

        Parameters:
            - "Pin": the GPIO pin in BCM numbering
            - "Values": Alternative values to publish for 0 and 1, defaults to
            CLOSED and OPEN for 0 and 1 respectively.
            - "PUD": Pull up or down setting, if "UP" uses PULL_UP, all other
            values result in PULL_DOWN.
            - "EventDetection": when set instead of depending on sensor_reporter
            to poll it will reliy on the event detection built into the GPIO
            library. Valid values are "RISING", "FALLING" and "BOTH". When not
            defined "Poll" must be set to a positive value.
        """
        super().__init__(publishers, params)

        self.pin = int(params("Pin"))

        # Allow users to override the 0/1 pin values.
        self.values = parse_values(params, ["CLOSED", "OPEN"])

        self.log.debug("Configured %s for CLOSED and %s for OPEN", self.values[0], self.values[1])

        pud = GPIO.PUD_UP if params("PUD") == "UP" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)
        
        #remember expacted state for contact closed
        self.state_when_closed = GPIO.LOW if pud == GPIO.PUD_UP else GPIO.HIGH

        # Set up event detection.
        try:
            event_detection = params("EventDetection")
            event_map = {"RISING": GPIO.RISING, "FALLING": GPIO.FALLING, "BOTH": GPIO.BOTH}
            if event_detection not in event_map:
                self.log.error("Invalid event detection specified: %s, one of RISING,"
                               " FALLING, BOTH or NONE are the only allowed values. "
                               "Defaulting to NONE",
                               event_detection)
                event_detection = "NONE"
        except NoOptionError:
            self.log.info("No event detection specified, falling back to polling")
            event_detection = "NONE"

        if event_detection != "NONE":
            GPIO.add_event_detect(self.pin, event_map[event_detection],
                                  callback=lambda channel: self.check_state())

        self.state = GPIO.input(self.pin)
        self.destination = params("Destination")

        if self.poll < 0 and event_detection == "NONE":
            raise ValueError("Event detection is NONE but polling is OFF")
        if self.poll > 0 and event_detection != "NONE":
            raise ValueError("Event detection is {} but polling is {}"
                             .format(event_detection, self.poll))
            
        # read optional button press config
        try:
            self.dest_short_press = params("Short_Press-Dest")
            try:
                #expect threshold in seconds
                self.short_press_time = float(params("Short_Press-Threshold"))
            except NoOptionError:
                self.short_press_time = 0
                
            try:
                self.dest_long_press = params("Long_Press-Dest")
                try:
                    self.long_press_time = float(params("Long_Press-Threshold"))
                except NoOptionError:
                    self.long_press_time = 0
                    self.log.error("No 'Long_Press-Threshold' configured for Long_Press-Dest: %s", self.dest_long_press)
            except NoOptionError:
                self.long_press_time = 0
        except NoOptionError:
            self.dest_short_press = None

        self.log.info("Configured RpiGpioSensor: pin %d on destination %s with PUD %s"
                      " and event detection %s", self.pin, self.destination, pud,
                      event_detection)

        # We've a first reading so publish it.
        self.publish_state()

    def check_state(self):
        """Checks the current state of the pin and if it's different from the
        last state publishes it. With event detection this method gets called
        when the GPIO pin changed states. When polling this method gets called
        on each poll.
        """
        value = GPIO.input(self.pin)
        if value != self.state:
            self.log.info("Pin %s changed from %s to %s", self.pin, self.state, value)
            self.state = value
            self.publish_state()
            self.check_button_press()

    def publish_state(self):
        """Publishes the current state of the pin."""
        msg = self.values[0] if self.state == GPIO.LOW else self.values[1]
        self._send(msg, self.destination)

    def check_button_press(self):
        """checks the duration the contact was closed and rises the event configured with that duration"""
        #if dest_short_press is not configured exit
        if self.dest_short_press is None:
            return
        
        #get time during button was closed
        if self.state == self.state_when_closed:
            self.high_time = datetime.datetime.now()
        else:
            time_delta_seconds = (datetime.datetime.now() - self.high_time).total_seconds()
            if time_delta_seconds > self.short_press_time:
                if self.long_press_time != 0 and time_delta_seconds > self.long_press_time:
                    self.log.info("Long button press occured on Pin %s (%s) was pressed for %s seconds", self.pin, self.dest_long_press, time_delta_seconds)
                    self.publish_button_state(is_short_press = False)
                else:
                    self.log.info("Short button press occured on Pin %s (%s) was pressed for %s seconds", self.pin, self.dest_short_press, time_delta_seconds)
                    self.publish_button_state(is_short_press = True)
    
    def publish_button_state(self, is_short_press):
        """send update to destination depending on button press duration"""
        current_time_str = str(datetime.datetime.now())
        #convert datetime to fromat: add T bewteen date and time
        curr_time_java = current_time_str[:10] + "T" + current_time_str[11:]
        if is_short_press:
            self._send(curr_time_java, self.dest_short_press)
        else:
            self._send(curr_time_java, self.dest_long_press)
                
    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        GPIO.cleanup()

class RpiGpioActuator(Actuator):
    """Allows for setting a GPIO pin to high or low on command. Also supports
    toggling.
    """

    def __init__(self, connections, params):
        """Initializes the GPIO subsystem and sets the pin to the InitialState.
        If InitialState is not povided in paams it defaults to GPIO.HIGH. If
        "Toggle" is defined on any message will result in the pin being set to
        HIGH for half a second and then back to LOW.

        Parameters:
            - "Pin": The GPIO pin in BCM numbering
            - "InitialState": The pin state to set when coming online, defaults
            to "OFF".
            - "Toggle": Optional parameter that when set to "True" causes any
            message received to result in setting the pin to HIGH, sleep for
            half a second, then back to LOW.
        """
        super().__init__(connections, params)
        self.pin = int(params("Pin"))
        GPIO.setup(self.pin, GPIO.OUT)

        try:
            self.invert = bool(strtobool(params("InvertOut")))
        except NoOptionError:
            self.invert = False
            
        try:
            self.toggle_cmd_src = params("ToggleCommandSrc")
            super()._register(self.toggle_cmd_src, self.on_message)
        except NoOptionError:
            pass

        try:
            self.init_state = GPIO.HIGH if params("InitialState") == "ON" else GPIO.LOW
        except NoOptionError:
            self.init_state = GPIO.LOW
        GPIO.output(self.pin, self.init_state)
        
        try:
            self.toggle = bool(strtobool(params("Toggle")))
        except NoOptionError:
            self.toggle = False
            
        #remember the current output state
        if self.toggle:
            self.currentState = None
        else:
            if self.invert:
                self.currentState = not self.init_state
            else:
                self.currentState = self.init_state
        
        self.lastToggle = None
        
        self.log.info("Configued RpoGpuiActuator: pin %d on destination %s with "
                      "toggle %s", self.pin, self.cmd_src, self.toggle)
        
        #publish inital state to cmd_src #TODO test function
        self._publish_actuator_state("ON" if self.currentState else "OFF", self.cmd_src)

    def on_message(self, msg):
        """Called when the actuator receives a message. If Toggle is not enabled
        sets the pin to HIGH if the message is ON and LOW if the message is OFF.
        """     
        # ignore command echo which occure with multiple connections: do nothing when the command (msg) equals the current state, ignor this on toggle mode
        if not self.toggle and not msg == "TOGGLE":
            if msg == "ON" or msg == "OFF":
                if self.currentState == strtobool(msg):
                    self.log.info("Revieved command for %s = %s which is equal to current output state. Ignoring command!", self.cmd_src, msg)
                    return
            elif len(msg) == 26 and msg[10] == "T":
                # If the string has length 26 and the char at index 10 is T then its porbably a java date time string
                if msg == self.lastToggle:
                    # filter datetime to make sure no double switching occures
                    self.log.info("Revieved toggle command for %s = %s with the same timestamp as before. Ignoring command!", self.toggle_cmd_src, msg)
                    return
                else:
                    # remember msg to filter double messages with same timestamp, set msg to Toggle for correct handling later on
                    self.lastToggle = msg
                    msg = "TOGGLE"
        
        self.log.info("Received command on %s: %s, Toggle = %s, Invert = %s, Pin = %d",
                      self.cmd_src, msg, self.toggle, self.invert, self.pin)

        # Toggle on then off.
        if self.toggle:
            self.log.info("Toggling pin %s %s to %s",
                          self.pin, self.highlow_to_str(self.init_state), self.highlow_to_str(not self.init_state))
            GPIO.output(self.pin, int(not self.init_state))
            # TODO switch the output back in separate function to unblock input on local connection!?
            sleep(.5)
            self.log.info("Toggling pin %s %s to %s",
                          self.pin, self.highlow_to_str(not self.init_state), self.highlow_to_str(self.init_state))
            GPIO.output(self.pin, self.init_state)

        # Turn ON/OFF based on the message.
        else:
            out = None
            if msg == "ON":
                out = GPIO.HIGH
            elif msg == "OFF":
                out = GPIO.LOW
            elif msg == "TOGGLE":
                out = int(not self.currentState)

            if out == None:
                self.log.error("Bad command %s", msg)
            else:
                self.currentState = out
                if self.invert:
                    out = int(not out)
                    
                self.log.info("Setting pin %d to %s", self.pin,
                              self.highlow_to_str(out))
                GPIO.output(self.pin, out)
                
                #publish own state back to remote connections
                self._publish_actuator_state("ON" if self.currentState else "OFF", self.cmd_src)
    
    @staticmethod            
    def highlow_to_str(output):
        """Converts (GPIO.)HIGH (=1) and LOW (=0) to the corresponding string
        
        Parameter: - "output": the GPIO constant (HIGH or LOW)
        
        Returns string HIGH/LOW
        """
        if output:
            return "HIGH"
        else:
            return "LOW"
