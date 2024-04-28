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
"""Contains RPI GPIO LED driver

Classes:
    - RpiGpioColourLED: Sets PWM for defined GPIOS
"""
from typing import Any, Dict
from types import SimpleNamespace
from copy import deepcopy
import yaml
import lgpio            # https://abyz.me.uk/lg/py_lgpio.html
from core.actuator import Actuator
from core import utils
from core import connection

class GpioColorLED(Actuator):
    """Uses Rpi_GPIO software PWM to control color LED's
    RGB and RGBW (red ,green, blue, white) LED's are supported.
    """

    def __init__(self,
                 connections:Dict[str, connection.Connection],
                 dev_cfg:Dict[str, Any]) -> None:
        """Initializes the GPIO subsystem and sets the pin to
        software PWM. Initialized the PWM duty cycle
        to the configured value.

        Expected yaml config:
        Class: gpio.gpio_led.GpioColorLED
        GpioChip            # The number of the GPIO chip to use
        Pin:                # The pin's to use for the RGBW PWM
            Red: x
            Green: y
            Blue: z
            White: 0
        InitialState:       # The inital state for the PWM duty cycle
            Red: x          # (0 = off, 100 = on, full brightness)
            Green: y
            Blue: z
            White: 100
        PWM-Frequency: 100  # The frequency for the PWM for all pin's
        InvertOut: True     # Whether to invert the output, true for common anode LED's
        Connections:        # The connections dict
            xxx
        """
        super().__init__(connections, dev_cfg)

        gpio_chip = int(dev_cfg["GpioChip"])
        try:
            self.chip_handle:int = lgpio.gpiochip_open(gpio_chip)
        except lgpio.error as err:
            self.log.error("%s could not setup GPIO chip %d. "
                           "Make sure the chip number is correct. Error Message: %s",
                           self.name, gpio_chip,err)
        # get pin config
        dev_cfg_pin:Dict[str, int] = dev_cfg["Pin"]
        self.pin = {}
        for color in utils.ColorHSV.C_RGBW_ARRAY:
            pin_no:int = dev_cfg_pin.get(color, 0)
            if pin_no != 0:
                # pin = 0, means it is not set. Ignore those!
                self.pin[color] = pin_no

        # get initial values (optional Parameter)
        dev_cfg_init_state:Dict[str, int] = dev_cfg.get("InitialState", {})
        if not isinstance(dev_cfg_init_state, dict):
            # debug: GPIO-Actuator Property "InitialState" might be in the DEFAULT section
            #        If this is the case and no local "InitialState" is configured
            #        this property might have the datatype bool, but we need a dict to proceed
            dev_cfg_init_state = {}
        self.state = SimpleNamespace(current=None, last=None)
        white_channel_in_use = utils.ColorHSV.C_WHITE in self.pin
        self.state.current = utils.ColorHSV(dev_cfg_init_state, white_channel_in_use)
        # init last state with configured color and full brightness for toggle command
        self.state.last = deepcopy(self.state.current)
        self.state.last.set_hsv(utils.ColorHSV.C_VAL, 100)

        # if output should be inverted, add -100 to all brightness_rgbw values
        self.invert = -100 if dev_cfg.get("InvertOut", True) else 0
        self.pwm_freq = dev_cfg.get("PWM-Frequency", 100)

        for (key, a_pin) in self.pin.items():
            try:
                # Claim output to make sure secondary pin functions are disabled
                # Otherwise output might not be off with PWM duty cycle = 0
                lgpio.gpio_claim_output(self.chip_handle, a_pin)
                # set get and set PWM frequency 100Hz
                # set PWM duty cycle to initial value for each color, respect invert option
                # set no pulse_cycles = repeat infinite
                lgpio.tx_pwm(self.chip_handle, a_pin, self.pwm_freq,
                             abs(self.invert + dev_cfg_init_state.get(key, 0)))
            except ValueError as err:
                self.log.error("%s could not setup GPIO Pin %d. "
                               "Make sure the pin number is correct. Error Message: %s",
                               self.name, self.pin, err)
        self.debounce = utils.Debounce(dev_cfg, default_debounce_time = 0.15)

        self.log.info("Configured GpioColorLED %s: pins %s",
                      self.name, self.pin)
        self.log.debug("%s LED's set to: %s and has following configured connections: \n%s",
                       self.name, self.state.current.rgbw_dict, yaml.dump(self.comm))

        # publish initial state to cmd_src
        self.publish_actuator_state()

        # register as HSV color datatyp so the received messages are same for
        # homie and openHAB-REST-API
        utils.configure_device_channel(self.comm, is_output=False,
                                       name="set color LED", datatype=utils.ChanType.COLOR,
                                       restrictions="hsv")
        # the actuator gets registered twice, at core-actuator and here
        # currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self,
                   msg:str) -> None:
        """ Called when the actuator receives a message.
            Changes LED PWM duty cycle according to the message.
            Expects comma separated values formated as HSV color: 'h,s,v'
            OR one value of: ON, OFF, TOGGLE, 0 to 100
        """
        new_color = deepcopy(self.state.current)
        #if msg.find(',') > 0 and msg.find('NaN') == -1:
        if ',' in msg and not 'NaN' in msg:
            # msg contains ',' so it should contain a 'h,s,v' string
            # in rare cases openHAB sends HSV value NaN, don't process these messages
            new_color.color_hsv_str = msg
        elif msg.isdigit():
            # msg contains digits convert it from string to int
            # store it as HSV value (brightness)
            new_color.set_hsv(utils.ColorHSV.C_VAL, int(msg))
        elif msg == "ON":
            # handle openHab item sending ON
            # set HSV value (brightness) to 100
            new_color.set_hsv(utils.ColorHSV.C_VAL, 100)
        elif msg == "OFF":
            # handle openHab item sending OFF
            # set HSV value (brightness) to 0
            new_color.set_hsv(utils.ColorHSV.C_VAL, 0)
        elif utils.is_toggle_cmd(msg):
            if self.debounce.is_within_debounce_time():
                # Filter close Toggle commands to ensure no double switching
                self.log.info("%s GpioColorLED received toggle command %s"
                              " within debounce time. Ignoring command!",
                             self.name, msg)
                return
            # invert current state on toggle command
            if self.state.current.get_hsv(utils.ColorHSV.C_VAL) > 0:
                # remember last value for  brightness for later
                self.state.last = deepcopy(self.state.current)
                new_color.set_hsv(utils.ColorHSV.C_VAL, 0)
            else:
                new_color = self.state.last

        else:
            # if command is not recognized ignore it
            self.log.warning("%s GpioColorLED received unrecognized command %s",
                             self.name, msg)
            return

        # do nothing when the command (new_color) equals the current state
        if self.state.current == new_color:
            self.log.info("%s GpioColorLED received %s"
                          " which is equal to current state. Ignoring command!",
                          self.name, new_color.rgbw_dict)
            return

        self.log.info("%s received %s, setting LEDs to %s",
                      self.name, msg, new_color.rgbw_dict)

        # set color for each channel
        for (color, set_point) in new_color.rgbw_dict.items():
            if color in self.pin:
                lgpio.tx_pwm(self.chip_handle, self.pin[color], self.pwm_freq,
                                 abs(self.invert + set_point))

        #publish own state back to remote connections
        self.state.current = new_color
        self.publish_actuator_state()

    def publish_actuator_state(self) -> None:
        """Publishes the current state of the actuator."""
        if len(self.pin) == 1:
            # if only one pin is defined publish only brightness state
            # to be compatible with openHab dimmer item
            self._publish(str(self.state.current.get_hsv(utils.ColorHSV.C_VAL)), self.comm)
            return
        self._publish(self.state.current.color_hsv_str, self.comm)

    def cleanup(self) -> None:
        """Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up GPIO outputs, invoked via Actuator %s",
                       self.name)
        for pin in self.pin.values():
            lgpio.gpio_free(self.chip_handle, pin)
        lgpio.gpiochip_close(self.chip_handle)
