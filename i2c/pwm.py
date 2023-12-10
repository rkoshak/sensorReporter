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
from types import SimpleNamespace
from threading import Thread
from time import sleep
from copy import deepcopy
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

    def __eq__(self, other_obj):
        ''' own implementation of compare equality to simplify code using this class
        '''
        if not isinstance(other_obj, ColorRGBW):
            # only compare to ColorRGBW class
            return NotImplemented
        return self._rgbw == other_obj.get_rgbw_dict

    def get_rgbw(self, color):
        ''' Returns the selected 'color' as an integer (range 0 to 100).
            Raises an error if the specified color is not in the internal color dictionary.
            Parameter:
                * color    String, one of "Red", "Green", "Blue", "White"
        '''
        if color in self._rgbw:
            return self._rgbw[color]
        raise ValueError(f'Parameter \'color\' has unknown value: {color}')

    def set_rgbw(self, color, value):
        ''' Sets the selected 'color' as in integer (range 0 to 100).
            Raises an error if the specified color is not in the internal color dictionary.
            Parameter:
                * color    String, one of "Red", "Green", "Blue", "White"
        '''
        if color in self._rgbw:
            self._rgbw[color] = value
        else:
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
        # Get color as HSV array
        hsv_array = self.color_hsv_array

        # Take HSV array and build hsv_color_str
        hsv_color_str = ( f'{int(hsv_array[0])},'
                          f'{int(hsv_array[1])},'
                          f'{int(hsv_array[2])}' )

        return hsv_color_str

    @color_hsv_str.setter
    def color_hsv_str(self, hsv_str):
        hsv = []
        # We expect a string with 3 values: hue,saturation,value
        # Split and convert them to integer
        for val in hsv_str.split(","):
            hsv.append(int(val))

        self.color_hsv_array = hsv

    @property
    def color_hsv_array(self):
        ''' Get or set the internal color in HSV color format
            as array with 3 fields:
            array index 0    : hue
            array index 1    : saturation
            array index 2    : value (brightness)
        '''
        # Build HSV color CSV array
        if self._rgbw[C_WHITE] == 0:
            # If white is not set use RGB values
            # Normalize RGB values and calculate HSV color
            hsv_tuple = colorsys.rgb_to_hsv(self._rgbw[C_RED]/100,
                                            self._rgbw[C_GREEN]/100,
                                            self._rgbw[C_BLUE]/100)
            # scale hsv_tuple and build array
            hsv_array = [hsv_tuple[0] * 360,
                         hsv_tuple[1] * 100,
                         hsv_tuple[2] * 100]
            if hsv_array[1] == 0:
                # Note: HSV 0,0,x seems to be out of range for openHAB item using 1,0,x instead
                # TODO: OpenHAB homie connections does not like 1,0,0
                hsv_array[0] = 1
        else:
            # Build HSV color array for case white color is set
            # Note: 0,0,x seems to be out of range for openHAB using 1,0,x instead
            hsv_array = [1,0,self._rgbw[C_WHITE]]
        return hsv_array

    @color_hsv_array.setter
    def color_hsv_array(self, hsv_array):
        # Check if saturation (hsv_array[1]) equals 0 then set RGB = 0 w = value (hsv_array)
        if hsv_array[1] == 0 and self.use_white_ch:
            # Set RGB to off if configured
            for color in C_RGB_ARRAY:
                self._rgbw[color] = 0
            # set white channel to saturation
            self._rgbw[C_WHITE] = hsv_array[2]
        else:
            # Convert HSV color to RGB color tuple
            color_rgb = colorsys.hsv_to_rgb(hsv_array[0]/360, hsv_array[1]/100, hsv_array[2]/100)
            # Set white channel to 0
            color_rgbw = color_rgb + (0,)
            # store converted values
            for (key, val) in zip(C_RGBW_ARRAY, color_rgbw):
                self._rgbw[key] = round(val * 100)

    @property
    def color_brightness(self):
        ''' Get or set the brightness as integer from 0 to 100 (= full brightness).
            If brightness is set to 0 color information is lost and
            setting it back to 100 will result in color white.
        '''
        return self.color_hsv_array[2]

    @color_brightness.setter
    def color_brightness(self, value):
        hsv_array = self.color_hsv_array
        hsv_array[2] = value
        self.color_hsv_array = hsv_array


class _SmoothDimmer():
    """ Handles smooth value changes and dimming commands
        to dim an actuator in a new thread
    """

    def __init__(self, caller, callback_set_pwm):
        """ Initialises dimmer relevant var's

        Parameters:
            - "caller"                : 'self' instance of the calling class
                                        The following objects are expected:
                                        - self.log                  : log instance of the actuator
                                        - self.name                 : name of the actuator
                                        - self.state.current        : current state of the actuator(int)
                                        - self.white_channel_in_use : whether a white LED is configured
                                        - self.dev_cfg              : device config dictionary
            - "callback_set_pwm"      : Callback method to access the PWM driver and set a value
                                          Prototype: 'def callback_set_pwm(value):'

        The following optional parameters are read from device config:
            - "SmoothChangeInterval"  : Time steps in seconds between PWM changes
                                        while smoothly switching on or off
            - "DimDelay"              : Delay in seconds befor starting to dim the PWM
            - "DimInterval"           : Time steps in seconds between PWM changes while dimming
        """
        self.caller = caller
        self.set_pwm = callback_set_pwm

        self.dimming = SimpleNamespace(interval = None, delay = None, state_before = 0)
        self.dimming.interval = float(caller.dev_cfg.get("DimInterval", 0.2))
        self.dimming.delay = float(caller.dev_cfg.get("DimDelay", 0.5))

        self.smooth_change = SimpleNamespace(interval = None, in_progress = False)
        self.smooth_change.interval = float(caller.dev_cfg.get("SmoothChangeInterval", 0.05))

        self._thread = None
        self._stop_thread = False

    def apply_value_change(self, value):
        """ Changes the PWM to the specified value.
            If 'SmoothChangeInterval' is configured to > 0 the value is changed shoothly
        """
        if self.smooth_change.interval:
            self._stop_thread = True
            self.smooth_change.in_progress = True
            self._start_thread(0, self.smooth_change.interval, value)
        else:
            # if interval == 0 set PWM directly
            self.set_pwm(value)

    def start_dimming(self):
        """ Handle manual dimming

            Start related thread to start dimming after configured
            'DimDelay' if stop_dimming() is not called
        """
        # ignore the DIM command if smooth_change.in_progress
        if not self.smooth_change.in_progress:
            self.dimming.state_before = deepcopy(self.caller.state.current)
            # set value to 0 if current state > 0
            # TODO migrate to deepcopy and color_brigthness
            color_array = self.caller.state.current.color_hsv_array
            brightness = color_array[2]
            if brightness:
                brightness = 0
            else:
                brightness = 100
            # set brightness
            color_array[2] = brightness
            # create new instance of ColorRGBW
            new_color = ColorRGBW(0, 0, 0, 0, self.caller.white_channel_in_use)
            new_color.color_hsv_array = color_array
            # start manual dimming with start_delay
            self._start_thread(self.dimming.delay, self.dimming.interval, new_color)

    def stop_dimming(self):
        """ Stops dimming thread if invoked by start_dimming()

            Returns new current_state if dimming has occurred otherwise 'None'.
            The calling class should store the returned current_state in it's on variable.
        """
        # make sure we don't interrupt the smooth change
        if not self.smooth_change.in_progress:
            # stop dimming thread and publish actuator state
            self._stop_thread = True
            if isinstance(self._thread, Thread):
                # Wait max. 200ms for the thread,
                # so that local connection call doesn't get stuck here.
                # otherwise short toggle event with local connections are not possible
                self._thread.join(timeout=0.2)
                # if thread is not alive = no timeout
                if not self._thread.is_alive():
                    # after thread closes check if the state (value) has changed
                    if self.dimming.state_before != self.caller.state.current:
                        # Return 'self.caller.state.current' to the caller,
                        # otherwise the new state will not be visible in the calling class
                        return self.caller.state.current
                else:
                    self.caller.log.debug("%s triac smooth dimmer thread still active,"
                                          " PWM value not published", self.caller.name)
        return None

    def _start_thread(self, start_delay, interval_time, value):
        """ Create a new thread to change the PWM in small steps,
            stop existing thread if present

            This is needed to unblock the calling thread, e. g. to make local
            connections work properly.
        """
        if isinstance(self._thread, Thread):
            # make sure thread is not running before starting another one
            self._thread.join(timeout=None)
        self._stop_thread = False
        self._thread = Thread(target=self._smooth_dimmer,
                              args=(start_delay, interval_time, value))
        # smooth_dimmer args=       |            |              |
        #                 start_delay            interval_time  target_value
        self._thread.start()

    def _smooth_dimmer(self, start_delay, interval_time, target_value):
        """ Change PWM-HAT smoothly to the target_value

        This method is used to create a thread for smoothly changeing the PWM when:
        * changeing to defined setpoint (start_delay = 0)
        * when manual dimming (start_delay > 0)

        Parameter:
            - "start_delay":     Delay in seconds befor starting the dimming
                                (0 = off, 0.1 steps)
            - "interval_time":   Time in seconds beween PWM steps
            - "target_value":    The ColorRGBW class object to dim to
        """
        # Manual dimming starts with a delay to ensure
        # that regular toggle commands still get through.
        waited = 0
        while waited < start_delay and not self._stop_thread:
            # sleep in 100ms steps to make the start_delay interruptible
            sleep(0.1)
            waited += 0.1
        current_value = self.caller.state.current
        target_brightness = target_value.color_brightness

        # loop until target value is reached or external stop trigger
        while current_value != target_value and not self._stop_thread:
            sleep(interval_time)
            for (color, target) in target_value.get_rgbw_dict.items():
                if abs(current_value.get_rgbw(color) - target) < 5:
                    current_value.set_rgbw(color, target)
                else:
                    if current_value.get_rgbw(color) < target:
                        current_value.set_rgbw(color, current_value.get_rgbw(color) + 5)
                    else:
                        current_value.set_rgbw(color, current_value.get_rgbw(color) - 5)
            self.set_pwm(current_value)

            if start_delay and current_value.color_brightness == 0 and target_brightness == 0:
                # if start_delay > 0 assume manual dimming,
                # set brightness to 100 for bidirectional dimming
                target_brightness = 100
                target_value.color_brightness = target_brightness

        # save value since its now the current state
        # TODO: since classes are only copied shallow following line is not needed
        self.caller.state.current = current_value
        self.smooth_change.in_progress = False


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
        self.state = SimpleNamespace(current=None, last=None)
        self.white_channel_in_use = self.channel[C_WHITE] != -1
        self.state.current = ColorRGBW(dev_cfg_init_state.get(C_RED, 0),
                                       dev_cfg_init_state.get(C_GREEN, 0),
                                       dev_cfg_init_state.get(C_BLUE, 0),
                                       dev_cfg_init_state.get(C_WHITE, 0),
                                       self.white_channel_in_use)
        # remember inverted state for toggle command
        self.state.last = ColorRGBW(abs(dev_cfg_init_state.get(C_RED, 0) -100),
                                    abs(dev_cfg_init_state.get(C_GREEN, 0) -100),
                                    abs(dev_cfg_init_state.get(C_BLUE, 0) -100),
                                    abs(dev_cfg_init_state.get(C_WHITE, 0) -100),
                                    self.white_channel_in_use)
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
            self.pwm[key].duty_cycle = scale_color_val(self.invert +
                                                       self.state.current.get_rgbw(key))

        # define callback method for smooth dimmer thread
        def set_pwm_value(value):
            for (key, pwm) in self.pwm.items():
                pwm.duty_cycle = scale_color_val(self.invert + value.get_rgbw(key))
        # read settings for the dimmer options, create instance of _SmoothDimmer
        self.dimmer = _SmoothDimmer(caller = self, callback_set_pwm = set_pwm_value)
        self.debounce = Debounce(dev_cfg, default_debounce_time = 0.15)

        self.log.info("Configured PWM-HAT %s: Channels: %s",
                      self.name, self.channel)
        self.log.debug("%s LED's set to: %s and has following configured connections: \n%s",
                       self.name, self.state.current.get_rgbw_dict, yaml.dump(self.comm))

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
        new_color = deepcopy(self.state.current)
        if msg.find(',') > 0 and msg.find('NaN') == -1:
            # msg contains ',' so it should contain a 'h,s,v' string
            # in rare cases openHAB sends HSV value NaN, don't process these messages
            new_color.color_hsv_str = msg
        elif msg == "ON":
            # handle openHab item sending ON
            # use last state to preserve color information
            new_color = deepcopy(self.state.last)
            # set HSV value (brightness) to 100
            new_color.color_brightness = 100
        elif msg == "OFF":
            # handle openHab item sending OFF
            if self.state.current.color_brightness != 0:
                # remember color for later
                self.state.last = deepcopy(self.state.current)
            # set HSV value (brightness) to 0
            new_color.color_brightness = 0
        elif msg == "DIM":
            self.dimmer.start_dimming()
            return
        elif msg == "STOP":
            # TODO check datatyp for current_state
            current_state = self.dimmer.stop_dimming()
            if current_state is not None:
                # remember current state
                self.state.current = current_state
                self.log.info("%s dimmed PWM-HAT channel %s to PWM %s",
                              self.name, self.channel, self.state.current.get_rgbw_dict)
                self.publish_actuator_state()

            return
        elif is_toggle_cmd(msg):
            if self.debounce.is_within_debounce_time():
                # filter close toggle commands to make sure no double switching occures
                self.log.info("%s PWM-HAT channel %s received toggle command %s"
                              " within debounce time. Ignoring command!",
                             self.name, self.channel, msg)
                return
            # invert current state on toggle command
            if self.state.current.color_brightness > 0:
                # remember last value for  brightness for later
                self.state.last = deepcopy(self.state.current)
                new_color.color_brightness = 0
            else:
                new_color = self.state.last

        else:
            # if command is not recognized ignore it
            self.log.warning("%s  PWM-HAT received unrecognized command %s",
                             self.name, msg)
            return

        # do nothing when the command (new_color) equals the current state
        if self.state.current == new_color:
            self.log.info("%s PWM-HAT received %s"
                          " which is equal to current state. Ignoring command!",
                          self.name, new_color.get_rgbw_dict)
            return

        self.log.info("%s received %s, setting LED to %s",
                      self.name, msg, new_color.get_rgbw_dict)

        self.dimmer.apply_value_change(new_color)
        # Publish own state back to remote connections
        self.state.current = new_color
        self.publish_actuator_state()

    def publish_actuator_state(self):
        """ Publishes the current state of the actuator."""
        self._publish(self.state.current.color_hsv_str, self.comm)


    def cleanup(self):
        """ Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up PWM HAT, invoked via Actuator %s", self.name)
        self.pwm_hat.deinit()
        self.pwm_hat.reset()
            