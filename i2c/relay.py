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
"""Contains EightRelayHAT.

Classes:
    - EightRelayHAT: switches the corresponding relay.
"""
from time import sleep
from distutils.util import strtobool
import datetime
import yaml
import lib8relay
from core.actuator import Actuator
from core.utils import is_toggle_cmd, configure_device_channel, ChanType

def onoff_to_str(output):
    """Converts 1 to "ON" and 1 to "OFF"

    Parameter: - "output": the switch constant (ON or OFF)

    Returns string ON/OFF
    """
    if output:
        return "ON"

    return "OFF"

class EightRelayHAT(Actuator):
    """Allows switching relay on Sequent Microsystems 8-Relays-HAT. Also supports
    toggling.
    """

    def __init__(self, connections, dev_cfg):
        """Initializes the I2C subsystem and sets the relay to the InitialState.
        If InitialState is not povided in params it defaults to OFF. If
        "SimulateButton" is defined on any message will result in the relay being set to
        ON for half a second and then back to OFF.

        Parameters:
            - "Stack": Stack Address 0..7
            - "Relay": Relay No. 1..8
            - "InitialState": The pin state to set when coming online, defaults
            to "OFF", optional.
            - "SimulateButton": Optional parameter that when set to "True" causes any
            message received to result in setting the pin to HIGH, sleep for
            half a second, then back to LOW.
        """
        super().__init__(connections, dev_cfg)

        self.stack = dev_cfg.get("Stack", 0)

        #relays on the HAT v5.3 are scrambled up, map them correctly
        #there is no relay 0 but array indexing starts at zero, first index is a filler
        relay_map = [0, 1, 2, 5, 6, 7, 8, 4, 3]

        self.relay = int(dev_cfg["Relay"])
        self.mapped_relay = relay_map[self.relay]

        #default state if not configured = False = off
        self.init_state =  dev_cfg.get("InitialState", False)

        try:
            lib8relay.set(self.stack, self.mapped_relay, self.init_state)
        except ValueError as err:
            self.log.error("%s could not setup EightRelayHAT. "
                           "Make sure the stack and relay "
                           "number is correct. Error Message: %s",
                           self.name, err)

        self.sim_button = dev_cfg.get("SimulateButton", False)

        #default debaunce time 0.15 seconds
        self.toggle_debounce = float(dev_cfg.get("ToggleDebounce", 0.15))
        self.last_toggle = datetime.datetime.fromordinal(1)

        #remember the current output state
        if self.sim_button:
            self.current_state = None
        else:
            self.current_state = self.init_state

        self.log.info("Configued EightRelayHAT %s: Stack %d, Relay %d (%s) with SimulateButton %s",
                      self.name, self.stack, self.relay,
                      onoff_to_str(self.init_state), self.sim_button)
        self.log.debug("%s has following configured connections: \n%s",
                       self.name, yaml.dump(self.comm))

        # publish inital state back to remote connections
        self.publish_actuator_state()

        configure_device_channel(self.comm, is_output=False,
                                 name="set digital output", datatype=ChanType.ENUM,
                                 restrictions="ON,OFF,TOGGLE")
        #the actuator gets registered twice, at core-actuator and here
        # currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self, msg):
        """Called when the actuator receives a message. If SimulateButton is not enabled
        sets the relay ON of OFF corresponding to the message.
        """
        # ignore command echo which occure with multiple connections:
        # do nothing when the command (msg) equals the current state,
        # ignor this on SimulateButton mode
        if not self.sim_button:
            if msg in ("ON", "OFF"):
                if self.current_state == strtobool(msg):
                    self.log.info("%s received command %s"
                                  " which is equal to current output state. Ignoring command!",
                                  self.name, msg)
                    return
            elif is_toggle_cmd(msg):
                # If the string has length 26 and the char at index 10
                # is T then its porbably a ISO 8601 formated datetime value,
                # which was send from RpiGpioSensor
                time_now = datetime.datetime.now()
                seconds_since_toggle = (time_now - self.last_toggle).total_seconds()
                if seconds_since_toggle < self.toggle_debounce:
                    # filter close toggle commands to make sure no double switching occures
                    self.log.info("%s received toggle command %s"
                                  " within debounce time. Ignoring command!",
                                  self.name, msg)
                    return

                self.last_toggle = time_now
                msg = "TOGGLE"

        self.log.info("%s received command %s, SimulateButton = %s, Stack = %d, Relay = %d",
                      self.name, msg, self.sim_button, self.stack, self.relay)

        # SimulateButton on then off.
        if self.sim_button:
            self.log.info("%s toggles Stack %d Relay %d,  %s to %s",
                          self.name, self.stack, self.relay,
                          onoff_to_str(self.init_state),
                          onoff_to_str(not self.init_state))
            lib8relay.set(self.stack, self.mapped_relay, int(not self.init_state))
            #  "sleep" will block a local connecten and therefore
            # distort the time detection of button press event's
            sleep(.5)
            self.log.info("%s toggles Stack %d Relay %d,  %s to %s",
                          self.name, self.stack, self.relay,
                          onoff_to_str(not self.init_state),
                          onoff_to_str(self.init_state))
            lib8relay.set(self.stack, self.mapped_relay, self.init_state)

        # Turn ON/OFF based on the message.
        else:
            out = None
            if msg == "ON":
                out = 1
            elif msg == "OFF":
                out = 0
            elif msg == "TOGGLE":
                out = int(not self.current_state)

            if out is None:
                self.log.error("%s bad command %s", self.name, msg)
            else:
                self.current_state = out

                self.log.info("%s set stack %d relay %d to %s",
                              self.name, self.stack, self.relay,
                              onoff_to_str(out))
                lib8relay.set(self.stack, self.mapped_relay, out)

                #publish own state back to remote connections
                self.publish_actuator_state()

    def publish_actuator_state(self):
        """Publishes the current state of the actuator."""
        msg = "ON" if self.current_state else "OFF"
        self._publish(msg, self.comm)
