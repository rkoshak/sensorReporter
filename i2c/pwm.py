# Copyright 2023 Daniel Decker
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


"""Contains Adafruit PWM HAT.

Classes:
    -  PwmHATColorLED: sets PWM for defined channels.
"""
from threading import Thread
import colorsys
import struct
import yaml
import board
import busio
import adafruit_pca9685
from core.actuator import Actuator
from core.utils import is_toggle_cmd, configure_device_channel, ChanType, Debounce

#constants
C_RED = "Red"
C_GREEN = "Green"
C_BLUE = "Blue"
C_WHITE = "White"
C_RGB_ARRAY = [C_RED, C_GREEN, C_BLUE]
C_RGBW_ARRAY = [C_RED, C_GREEN, C_BLUE, C_WHITE]

def scale_color_val(value):
    """ scale input value (range 0 to 100)
        to fit PWM HAT duty cycle (range 0x0 to 0xffff)
    """
    val = abs(value) / 100
    return int(val * 0xffff)

class ColorRGBW():
    ''' Stores RGBW color values, which can range from 0 (= off) to 100 (= full brightness).
        Allows read access to individual colors and a dictionary of all RGBW values.
        Exposed property to set and get color in HSV format as CSV
        e. g. green with full brightness =  '120,100,100'
    '''
    def __init__(self, red, green, blue, white, use_white_channel):
        ''' Initializes colors to a given value (range 0 to 100)
            Parameters:
                * red, green, blue, white    Integer that defines the initial value for
                                             the selected color.
                                             Range: 0 (= off) to 100 (= full brightness)
                * use_white_channel          Boolean, if true the 'color_hsv_str' property assumes
                                             a white LED is present.
                                             So HSV color 0,0,100 (no saturation) will be
                                             converted to RGBW {red: 0, green: 0, blue:0, white:100}
                                             If false: HSV color 0,0,100 will result in RGBW
                                             {red: 100, green: 100, blue:100, white:0}
        '''
        if white != 0:
            red = 0
            green = 0
            blue = 0

        self._rgbw = {
            C_RED   : red,
            C_GREEN : green,
            C_BLUE  : blue,
            C_WHITE : white
            }
        self.use_white_ch = use_white_channel

    def get_rgbw(self, color):
        ''' Returns the  selected 'color' as an integer (range 0 to 100).
            Raises an error if the specified color is not in the internal color dictionary.
            Parameter:
                * color    String, one of "Red", "Green", "Blue", "White"
        '''
        if color in self._rgbw:
            return self._rgbw[color]
        raise ValueError(f'Parameter \'color\' has unknown value: {color}')

    @property
    def get_rgbw_dict(self):
        ''' Returns internal RGBW color dictionary for debugging and log messages
        '''
        return self._rgbw

    @property
    def color_hsv_str(self):
        ''' Get or set the internal color in HSV color format
            as comma separated value string without spaces: hue,saturation,value
            E. g. pure red in full brightness = '0,100,100'
        '''
        # Build HSV color CSV str
        if self._rgbw[C_WHITE] == 0:
            # If white is not set use RGB values
            # Normalize RGB values and calculate HSV color
            hsv_tuple = colorsys.rgb_to_hsv(self._rgbw[C_RED]/100,
                                            self._rgbw[C_GREEN]/100,
                                            self._rgbw[C_BLUE]/100)
            # Take HSV_tuple scale it and build hsv_color_str
            hsv_color_str = ( f'{int(hsv_tuple[0]*360)},'
                              f'{int(hsv_tuple[1]*100)},'
                              f'{int(hsv_tuple[2]*100)}' )
        else:
            # Build HSV color str for case white color is set
            # Note: 0,0,x seems to be out of range for openHAB using 1,0,x instead
            hsv_color_str = f"1,0,{int(self._rgbw[C_WHITE])}"
            # In white mode RGB colors a not supported
            #for color in C_RGB_ARRAY:
            #    brightness_rgbw[color] = 0
        return hsv_color_str

    @color_hsv_str.setter
    def color_hsv_str(self, hsv_str):
        hsv = []
        # We expect a string with 3 values: h,s,v
        # Split and convert them to integer
        for val in hsv_str.split(","):
            hsv.append(int(val))

        # Check if saturation (hsv[1]) equals 0 then set RGB = 0 w = value (hsv[2])
        if hsv[1] == 0 and self.use_white_ch:
            # Set RGB to off if configured
            for color in C_RGB_ARRAY:
                self._rgbw[color] = 0
            # set white channel to saturation
            self._rgbw[C_WHITE] = hsv[2]
        else:
            # Convert HSV color to RGB color tuple
            color_rgb = colorsys.hsv_to_rgb(hsv[0]/360, hsv[1]/100, hsv[2]/100)
            # Set white channel to 0
            color_rgbw = color_rgb + (0,)
            # store converted values
            for (key, val) in zip(C_RGBW_ARRAY, color_rgbw):
                self._rgbw[key] = round(val * 100)


class PwmHatColorLED(Actuator):
    """ Allows to use 3 or 4 PWM channel to be dimmed on Adafruit 16-Channel PWM/Servo HAT.
        Also supports toggling.
        Documentation for the device is available at:
        https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi/overview
    """

    def __init__(self, connections, dev_cfg):
        """ Initializes the PWM HAT.
            Initializes the PWM duty cycle
            to the configured value.

        Expected YAML config:
        Class: i2c.pwm.PwmHatColorLED
        Channels:           #the pin's to use for the RGBW PWM
            Red: x
            Green: y
            Blue: z
            White: 0
        InitialState:       #the initial state for the PWM duty cycle
            Red: x          #(0 = off, 100 = on, full brightness)
            Green: y
            Blue: z
            White: 100
        PWM-Frequency: 240  #the frequency for the PWM for all pin's
        InvertOut: True     #whether to invert the output, true for common anode LED's
        Stack: 0            #Optional, Stack address (I2C)
        Connections:        #the connections dictionary
            xxx
        """
        super().__init__(connections, dev_cfg)

        # Get optional Stack address as decimal, offset 0x40 is added internally
        self.stack = dev_cfg.get("Stack", 0) + 0x40

        # Get channel No. in device config
        dev_cfg_ch = dev_cfg["Channels"]
        self.channel = {}
        for color in C_RGBW_ARRAY:
            # valid channel are 0-15, use -1 for undefined
            self.channel[color] = dev_cfg_ch.get(color, -1)

        # Get initial values (optional Parameter)
        dev_cfg_init_state = dev_cfg.get("InitialState", {})
        if not isinstance(dev_cfg_init_state, dict):
            # Debug: Actuator Property "InitialState" might be in the DEFAULT section
            #        If this is the case and no local "InitialState" is configured
            #        this property might have the datatype bool, but we need a dict to proceed
            dev_cfg_init_state = {}
        white_channel_in_use = self.channel[C_WHITE] != -1
        self.color = ColorRGBW(dev_cfg_init_state.get(C_RED, 0),
                               dev_cfg_init_state.get(C_GREEN, 0),
                               dev_cfg_init_state.get(C_BLUE, 0),
                               dev_cfg_init_state.get(C_WHITE, 0),
                               white_channel_in_use)

        # If output should be inverted, add -100 to all brightness_rgbw values
        self.invert = -100 if dev_cfg.get("InvertOut", True) else 0

        # Set up Adafruit PWM HAT
        try:
            i2c_pins = busio.I2C(board.SCL, board.SDA)
            # Create one own instance of PCA9685 for every actuator,
            # there seams to be no problem with concurrency
            self.pwm_hat = adafruit_pca9685.PCA9685(i2c_pins, address = self.stack)
            # Set frequency, all channels share same value
            self.pwm_hat.frequency = int(dev_cfg.get("PWM-Frequency", 240))
        except ValueError as err:
            self.log.error("%s could not setup PWM HAT. Stack No. out of Range (allowed 0-31) "
                           "or no device with given stack address. Error Message: %s",
                           self.name, err)
            return
        except struct.error as err:
            self.log.error("%s could not setup PWM HAT. PWM-Frequency out of Range "
                           "(allowed 30 - 1600). Error Message: %s",
                           self.name, err)
            return

        self.pwm = {}
        for (key, a_ch) in self.channel.items():
            if a_ch == -1:
                continue
            # Get channel object
            # Note: adafruit_pca9685 won't throw an error if one channel is taken multiple times
            self.pwm[key] = adafruit_pca9685.PWMChannel(self.pwm_hat, a_ch)
            # Set PWM duty cycle to initial value for each color, respect invert option
            self.pwm[key].duty_cycle = scale_color_val(self.invert + self.color.get_rgbw(key))

        self.log.info("Configured PWM-HAT %s: Channels: %s",
                      self.name, self.channel)
        self.log.debug("%s LED's set to: %s and has following configured connections: \n%s",
                       self.name, self.color.get_rgbw_dict, yaml.dump(self.comm))

        # Publish initial state to cmd_src
        self.publish_actuator_state()

        # Register as HSV color datatyp so the received messages are same for
        # homie and openHAB-REST-API
        configure_device_channel(self.comm, is_output=False,
                                 name="set color LED", datatype=ChanType.COLOR,
                                 restrictions="hsv")
        # The actuator gets registered twice, at core-actuator and here
        # currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self, msg):
        """ Called when the actuator receives a message.
            Changes LED PWM duty cycle according to the message.
            Expects comma separated values formated as HSV color: 'h,s,v'
        """
        self.color.color_hsv_str = msg

        for (key, pwm) in self.pwm.items():
            pwm.duty_cycle = scale_color_val(self.invert + self.color.get_rgbw(key))

        self.log.info("%s received %s, setting LED to %s",
                      self.name, msg, self.color.get_rgbw_dict)

        # Publish own state back to remote connections
        self.publish_actuator_state()

    def publish_actuator_state(self):
        """ Publishes the current state of the actuator."""
        self._publish(self.color.color_hsv_str, self.comm)


    def cleanup(self):
        """ Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up PWM HAT, invoked via Actuator %s", self.name)
        self.pwm_hat.deinit()
        self.pwm_hat.reset()
            