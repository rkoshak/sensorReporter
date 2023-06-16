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
import colorsys
import yaml
from RPi import GPIO
from core.actuator import Actuator
from core.utils import verify_connections_layout, configure_device_channel, ChanType
from gpio.rpi_gpio import set_gpio_mode

#constants
C_RED = "Red"
C_GREEN = "Green"
C_BLUE = "Blue"
C_WHITE = "White"


class GpioColorLED(Actuator):
    """Uses Rpi_GPIO software PWM to control color LED's
    RGB and RGBW (red ,green, blue, white) LED's are supported.
    """

    def __init__(self, connections, dev_cfg):
        """Initializes the GPIO subsystem and sets the pin to
        software PWM. Initalized the PWM duty cycle
        to the configured value.

        Expected yaml config:
        Class: gpio.gpio_led.GpioColorLED
        Pin:                #the pin's to use for the RGBW PWM
            Red: x
            Green: y
            Blue: z
            White: 0
        InitialState:       #the inital state for the PWM duty cycle
            Red: x          #(0 = off, 100 = on, full brigtness)
            Green: y
            Blue: z
            White: 100
        PWM-Frequency: 100  #the frequecy for the PWM for all pin's
        InvertOut: True     #whether to invert the output, true for common anode LED's 
        Connections:        #the connections dict
            xxx
        """
        super().__init__(connections, dev_cfg)
        self.gpio_mode = set_gpio_mode(dev_cfg, self.log)

        #get pin config
        dev_cfg_pin = dev_cfg["Pin"]
        self.pin = {}
        self.pin[C_RED] = dev_cfg_pin.get(C_RED, 0)
        self.pin[C_GREEN] = dev_cfg_pin.get(C_GREEN, 0)
        self.pin[C_BLUE] = dev_cfg_pin.get(C_BLUE, 0)
        self.pin[C_WHITE] = dev_cfg_pin.get(C_WHITE, 0)

        #get inital values (optional Parameter)
        dev_cfg_init_state = dev_cfg.get("InitialState", {})
        if not isinstance(dev_cfg_init_state, dict):
            #debug: GPIO-Actuator Property "InitialState" might be in the DEFAULT section
            #        If this is the case and no local "InitialState" is configured
            #        this property might have the datatype bool, but we need a dict to proceed
            dev_cfg_init_state = {}
        brightness_rgbw = {}
        brightness_rgbw[C_RED] = dev_cfg_init_state.get(C_RED, 0)
        brightness_rgbw[C_GREEN] = dev_cfg_init_state.get(C_GREEN, 0)
        brightness_rgbw[C_BLUE] = dev_cfg_init_state.get(C_BLUE, 0)
        brightness_rgbw[C_WHITE]= dev_cfg_init_state.get(C_WHITE, 0)

        #build hsv color str
        if brightness_rgbw[C_WHITE] == 0:
            #if not white is set use RGB values
            #normalize rgb values and calculate hsv color
            hsv_tuple = colorsys.rgb_to_hsv(brightness_rgbw[C_RED]/100,
                                             brightness_rgbw[C_GREEN]/100,
                                             brightness_rgbw[C_BLUE]/100)
            #take hsv_tuple scale it and build hsv_color_str
            self.hsv_color_str = ( f'{int(hsv_tuple[0]*360)},'
                                   f'{int(hsv_tuple[1]*100)},'
                                   f'{int(hsv_tuple[2]*100)}' )
        else:
            #build hsv color str for case white color is set
            #note: 0,0,x seems to be out of range for openHAB using 1,0,x instead
            self.hsv_color_str = f"1,0,{int(brightness_rgbw[C_WHITE])}"
            #in white mode rgb colors a not supported
            brightness_rgbw[C_RED] = 0
            brightness_rgbw[C_GREEN] = 0
            brightness_rgbw[C_BLUE] = 0

        #if output shoude be inverted, add -100 to all brightness_rgbw values
        self.invert = -100 if dev_cfg.get("InvertOut", True) else 0

        self.pwm = {}
        for (key, a_pin) in self.pin.items():
            if a_pin == 0:
                continue
            try:
                GPIO.setup(a_pin, GPIO.OUT)
                #set get and set PWM frequency 100Hz
                self.pwm[key] = GPIO.PWM(a_pin, dev_cfg.get("PWM-Frequency", 100))
                #set PWM duty cycle to inital value for each color, respect invert option
                self.pwm[key].start(abs(self.invert + brightness_rgbw[key]))
            except ValueError as err:
                self.log.error("%s could not setup GPIO Pin %d (%s). "
                               "Make sure the pin number is correct. Error Message: %s",
                               self.name, self.pin, self.gpio_mode, err)

        #verify that defined output channels in Connections section are valid
        verify_connections_layout(self.comm, self.log, self.name)

        self.log.info("Configued GpioColorLED %s: pin numbering %s, and pins\n%s",
                      self.name, self.gpio_mode, self.pin)
        self.log.debug("%s LED's set to: %s and has following configured connections: \n%s",
                       self.name, brightness_rgbw, yaml.dump(self.comm))

        # publish inital state to cmd_src
        self.publish_actuator_state()

        #register as HSV color datatyp so the revieved messages are same for
        #homie and openHAB-REST-API
        configure_device_channel(self.comm, is_output=False,
                                 name="set color LED", datatype=ChanType.COLOR,
                                 restrictions="hsv")
        #the actuator gets registered twice, at core-actuator and here
        # currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self, msg):
        """Called when the actuator receives a message. 
        Changes LED PWM duty cycle according to the message.
        Expects comma separated values formated as HSV color: 'h,s,v'
        """
        self.hsv_color_str = msg
        brightness_rgbw = {}
        hsv = []
        #we expect a string with 3 values: h,s,v
        #split and convert them to integer
        for val in msg.split(","):
            hsv.append(int(val))

        #check if saturation (hsv[1]) equals 0 then set rgb = 0 w = value (hsv[2])
        if hsv[1] == 0 and C_WHITE in self.pwm:
            #set rgb to off if configured
            for color in (C_RED, C_GREEN, C_BLUE):
                if color in self.pwm:
                    brightness_rgbw[color] = 0
                    self.pwm[color].ChangeDutyCycle(abs(self.invert))
            brightness_rgbw[C_WHITE] = hsv[2]
            self.pwm[C_WHITE].ChangeDutyCycle(abs(self.invert + brightness_rgbw[C_WHITE]))
        else:
            #convert HSV color to RGB color tuple
            rgb = colorsys.hsv_to_rgb(hsv[0]/360, hsv[1]/100, hsv[2]/100)
            #set white channel to 0
            rgbw = rgb + (0,)
            #interrate over self.pin.keys() to make sure there are alway 4 items like in rgbw
            for (key, val) in zip(self.pin.keys(), rgbw):
                if key in self.pwm:
                    #remember recieved brightnes
                    brightness_rgbw[key] = round(val * 100)
                    #change PWM duty cycle to new brightnes, respect invert option
                    self.pwm[key].ChangeDutyCycle(abs(self.invert + brightness_rgbw[key]))

        self.log.info("%s recieved %s, setting LED to %s",
                      self.name, msg, brightness_rgbw)

        #publish own state back to remote connections
        self.publish_actuator_state()

    def publish_actuator_state(self):
        """Publishes the current state of the actuator."""
        self._publish(self.hsv_color_str, self.comm)

    def cleanup(self):
        """Disconnects from the GPIO subsystem."""
        self.log.debug("Cleaning up GPIO outputs, invoked via Actuator %s (%s)",
                       self.name, self.gpio_mode)
        # make sure cleanup runs only once
        if GPIO.getmode() is not None:
            GPIO.cleanup()
