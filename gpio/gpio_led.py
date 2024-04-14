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
from typing import Any
import colorsys
import yaml
import lgpio            # https://abyz.me.uk/lg/py_lgpio.html
from core.actuator import Actuator
from core import utils
from core import connection

#constants
C_RED = "Red"
C_GREEN = "Green"
C_BLUE = "Blue"
C_WHITE = "White"
C_RGBW_ARRAY = [C_RED, C_GREEN, C_BLUE, C_WHITE]


class GpioColorLED(Actuator):
    """Uses Rpi_GPIO software PWM to control color LED's
    RGB and RGBW (red ,green, blue, white) LED's are supported.
    """

    def __init__(self,
                 connections:dict[str, connection.Connection],
                 dev_cfg:dict[str, Any]) -> None:
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
        dev_cfg_pin:dict[str, int] = dev_cfg["Pin"]
        self.pin = {}
        self.pin[C_RED] = dev_cfg_pin.get(C_RED, 0)
        self.pin[C_GREEN] = dev_cfg_pin.get(C_GREEN, 0)
        self.pin[C_BLUE] = dev_cfg_pin.get(C_BLUE, 0)
        self.pin[C_WHITE] = dev_cfg_pin.get(C_WHITE, 0)
        for color in C_RGBW_ARRAY:
            if self.pin[color] == 0:
                # remove pin from dict since it is not specified
                self.pin.pop(color)

        # get inital values (optional Parameter)
        dev_cfg_init_state:dict[str, int] = dev_cfg.get("InitialState", {})
        if not isinstance(dev_cfg_init_state, dict):
            # debug: GPIO-Actuator Property "InitialState" might be in the DEFAULT section
            #        If this is the case and no local "InitialState" is configured
            #        this property might have the datatype bool, but we need a dict to proceed
            dev_cfg_init_state = {}
        brightness_rgbw:dict[str, int] = {}
        brightness_rgbw[C_RED] = dev_cfg_init_state.get(C_RED, 0)
        brightness_rgbw[C_GREEN] = dev_cfg_init_state.get(C_GREEN, 0)
        brightness_rgbw[C_BLUE] = dev_cfg_init_state.get(C_BLUE, 0)
        brightness_rgbw[C_WHITE]= dev_cfg_init_state.get(C_WHITE, 0)


        # build hsv color str
        if brightness_rgbw[C_WHITE] == 0:
            # if not white is set use RGB values
            # normalize rgb values and calculate hsv color
            hsv_tuple = colorsys.rgb_to_hsv(brightness_rgbw[C_RED]/100,
                                             brightness_rgbw[C_GREEN]/100,
                                             brightness_rgbw[C_BLUE]/100)
            # take hsv_tuple scale it and build hsv_color_str
            self.hsv_color_str = ( f'{int(hsv_tuple[0]*360)},'
                                   f'{int(hsv_tuple[1]*100)},'
                                   f'{int(hsv_tuple[2]*100)}' )
        else:
            # build hsv color str for case white color is set
            #note: 0,0,x seems to be out of range for openHAB using 1,0,x instead
            self.hsv_color_str = f"1,0,{int(brightness_rgbw[C_WHITE])}"
            #in white mode rgb colors a not supported
            brightness_rgbw[C_RED] = 0
            brightness_rgbw[C_GREEN] = 0
            brightness_rgbw[C_BLUE] = 0

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
                             abs(self.invert + brightness_rgbw[key]))
            except ValueError as err:
                self.log.error("%s could not setup GPIO Pin %d. "
                               "Make sure the pin number is correct. Error Message: %s",
                               self.name, self.pin, err)

        self.log.info("Configured GpioColorLED %s: pins %s",
                      self.name, self.pin)
        self.log.debug("%s LED's set to: %s and has following configured connections: \n%s",
                       self.name, brightness_rgbw, yaml.dump(self.comm))

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
        """Called when the actuator receives a message.
        Changes LED PWM duty cycle according to the message.
        Expects comma separated values formated as HSV color: 'h,s,v'
        """
        self.hsv_color_str = msg
        brightness_rgbw:dict[str, int] = {}
        hsv:list[int] = []
        #we expect a string with 3 values: h,s,v
        #split and convert them to integer
        for part in msg.split(","):
            hsv.append(int(part))

        #check if saturation (HSV[1]) equals 0 then set RGB = 0 w = value (HSV[2])
        if hsv[1] == 0 and C_WHITE in self.pin:
            #set RGB to off if configured
            for color in (C_RED, C_GREEN, C_BLUE):
                if color in self.pin:
                    brightness_rgbw[color] = 0
                    lgpio.tx_pwm(self.chip_handle, self.pin[color], self.pwm_freq,
                                 abs(self.invert))
            brightness_rgbw[C_WHITE] = hsv[2]
            lgpio.tx_pwm(self.chip_handle, self.pin[C_WHITE], self.pwm_freq,
                         abs(self.invert + brightness_rgbw[C_WHITE]))
        else:
            #convert HSV color to RGB color tuple
            rgb = colorsys.hsv_to_rgb(hsv[0]/360, hsv[1]/100, hsv[2]/100)
            #set white channel to 0
            rgbw = rgb + (0,)
            #iterate over self.pin.keys() to make sure there are always 4 items like in rgbw
            for (color, val) in zip(C_RGBW_ARRAY, rgbw):
                if color in self.pin:
                    #remember received brightness
                    brightness_rgbw[color] = round(val * 100)
                    #change PWM duty cycle to new brightness, respect invert option
                    lgpio.tx_pwm(self.chip_handle, self.pin[color], self.pwm_freq,
                                 abs(self.invert + brightness_rgbw[color]))

        self.log.info("%s received %s, setting LED to %s",
                      self.name, msg, brightness_rgbw)

        #publish own state back to remote connections
        self.publish_actuator_state()

    def publish_actuator_state(self) -> None:
        """Publishes the current state of the actuator."""
        self._publish(self.hsv_color_str, self.comm)

    def cleanup(self) -> None:
        """Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up GPIO outputs, invoked via Actuator %s",
                       self.name)
        for pin in self.pin.values():
            lgpio.gpio_free(self.chip_handle, pin)
        lgpio.gpiochip_close(self.chip_handle)
