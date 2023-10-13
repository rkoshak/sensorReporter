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


"""Contains TriacHAT.

Classes:
    - TriacHAT: 2 channel triac for light dimming.
"""
from types import SimpleNamespace
from threading import Thread
from time import sleep
import smbus2       # https://smbus2.readthedocs.io/en/latest/
import yaml
from core.actuator import Actuator
from core.utils import is_toggle_cmd, configure_device_channel, ChanType, Debounce

# Constans for 2-CH_TRIAC_HAT Register addresses
# https://www.waveshare.com/wiki/2-CH_TRIAC_HAT
REG_MODE = 0x01
REG_CHANNEL_ENABLE = 0x02
REG_CHANNEL1_ANGLE = 0x03
REG_CHANNEL2_ANGLE = 0x04
REG_GRID_FREQUENCY = 0x05
REG_RESET = 0x06
CHANNEL1_ENABLE = 0x01
CHANNEL2_ENABLE = 0x02

class _I2cDriver():
    """
        The i2c driver handles communication with the waveshare 2-CH triac HAT.
        Documentation for the device is available at:
        https://www.waveshare.com/wiki/2-CH_TRIAC_HAT

        Depends on smbus2,
        uses I2C address 0x47, which is hardcoded on the hardware

        Public interfaces:
            - set_duty_cycle
            - set_power_grid_frequency
    """
    def __init__(self):
        self.bus = smbus2.SMBus(1)   # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        # the triac uses bus address 0x47, the HAT is hardcoded to this address
        self.addr = 0x47
        # remember enabled channels / 0 = off, 1 = ch1 on, 2 = ch2 on, 3= ch1 & ch2 on
        self.enabled_channels = 0x00

        #set mode to "Voltage adjustment"
        self._bus_write(REG_MODE, 1)

    def _bus_write(self, reg, data):
        """ The triac HAT expects the date to be written in the following structure:
         +----------+---------------+-----------+----------+
         | I2C addr | register addr | high byte | low byte |
         +----------+---------------+-----------+----------+
                                    |    payload data      |
                                    +----------------------+
         The payload must be a word (2 bytes), but the registers only evaluate
         the high byte. The low byte seems to be ignored. Therefore bit shift the
         data one byte (8 bit) to the left.

        Parameters:
            - "reg":    Register to write to (see REG-constants above)
            - "date":   The data to write into the given register (number 1 byte)
        """
        self.bus.write_word_data(self.addr, reg, (data << 8))


    def set_duty_cycle(self, log, channel, duty_cycle_pct):
        """Changes the PWM duty cycle & enabled / disables the specified channel on demand

        Parameters:
            - "log":            The self.log instance of the calling actuator
            - "channel":        The channel of the triac HAT, allowed values 1 & 2
            - "duty_cycle_pct": Duty cycle in percent, allowed values 0 - 100

        duty_cycle_pct = 0 will switch off the channel, while 100 will set it to alway on
        """
        # validate given channel
        if channel < 1 or channel > 2:
            log.error("Channel out of bounds, allowed 1 & 2! Value: %s", channel)
            return
        # validate given duty_cycle_pct
        if duty_cycle_pct < 0 or duty_cycle_pct > 100:
            log.error("PWM (duty_cycle_pct) out of range, 0-100 allowed! Value: %s",
                      duty_cycle_pct)
            return

        channels_last_state = self.enabled_channels
        # check if channel 1 or 2 needs the be enabled / disabled
        if  duty_cycle_pct > 0:
            if channel == 1:
                # enable channel 1
                self.enabled_channels = self.enabled_channels | CHANNEL1_ENABLE
            else:
                # enable channel 2
                self.enabled_channels = self.enabled_channels | CHANNEL2_ENABLE
        else:
            if channel == 1:
                # preserve channel 2 setting, disable ch 1
                self.enabled_channels = self.enabled_channels & CHANNEL2_ENABLE
            else:
                # preserve channel 1 setting, disable ch 2
                self.enabled_channels = self.enabled_channels & CHANNEL1_ENABLE

        # only write channel register on change
        if channels_last_state != self.enabled_channels:
            # Before enabling or disabeling the selected channel set angel to zero
            # otherwise PWM will turn on fully for a short time, when enabling
            if channel == 1:
                self._bus_write(REG_CHANNEL1_ANGLE, 0)
            elif channel == 2:
                self._bus_write(REG_CHANNEL2_ANGLE, 0)
            sleep(0.05)

            log.debug("Triac driver updated enabled_channels to %d", self.enabled_channels)
            self._bus_write(REG_CHANNEL_ENABLE, self.enabled_channels)
            # wait 50ms so the HAT can proecess the command
            sleep(0.05)

        # the triac expects values from 0 to 179,
        # convert duty_cycle_pct to expected angel values
        angle = round( duty_cycle_pct / 100 * 179 )

        # select the correct register for the given channel
        if channel == 1:
            self._bus_write(REG_CHANNEL1_ANGLE, angle)
        elif channel == 2:
            self._bus_write(REG_CHANNEL2_ANGLE, angle)

        log.debug("Triac driver dimming channel %d to PWM %d%%",
                           channel, duty_cycle_pct)

    def set_power_grid_frequency(self, log, frequency):
        """Tells the triac the mains frequency, to set the PWM accordingly

        Parameters:
            - "log":        The self.log instance of the calling actuator
            - "frequency":  The power grid frequency in Hz, allowed values 50 & 60
        """
        if frequency in [50, 60]:
            self._bus_write(REG_GRID_FREQUENCY, frequency)
            # wait 50ms so the HAT can proecess the command
            sleep(0.05)
        else:
            log.warning("Unsupported mains frequency %s! Frequency not set", frequency)

# create one instance of _I2cDriver() for later use
try:
    _driver_singleton = _I2cDriver()
except OSError:
    # catch triac Hat not set up for i2c
    _driver_singleton = None
def i2c_driver():
    """ Use the singleton pattern to make sure only one instance for _I2cDriver()
        is created even with multiple TriacDimmer
        https://code.activestate.com/recipes/52558/#c7
    """
    return _driver_singleton


class _SmoothDimmer():
    """ Handles smooth value changes and dimming commands
        to dim an actuator in a new thread
    """

    def __init__(self, caller, callback_set_pwm):
        """ Initialises dimmer relevant var's

        Parameters:
            - "caller"                  : 'self' instance of the calling class
                                          The following objects are expected:
                                          - self.log            : log instance of the actuator
                                          - self.name           : name of the actuator
                                          - self.state.current  : current state of the actuator(int)
                                          - self.dev_cfg        : device config dictionary
            - "callback_set_pwm"        : Callback method to access the PWM driver and set a value
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
            self.dimming.state_before = self.caller.state.current
            # set value to 0 if current state > 0
            if self.caller.state.current:
                value = 0
            else:
                value = 100
            # start manual dimming with start_delay
            self._start_thread(self.dimming.delay, self.dimming.interval, value)

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
        """ Change triac PWM smoothly to the target_value

        This method is used to create a thread for smoothly changeing the PWM when:
        * changeing to defined setpoint (start_delay = 0)
        * when manual dimming (start_delay > 0)

        Parameter:
            - "start_delay":     Delay in seconds befor starting the dimming
                                (0 = off, 0.1 steps)
            - "interval_time":   Time in seconds beween PWM steps
            - "target_value":    The PWM percentage to dim to
        """
        # Manual dimming starts with a delay to ensure
        # that regular toggle commands still get through.
        waited = 0
        while waited < start_delay and not self._stop_thread:
            # sleep in 100ms steps to make the start_delay interruptable
            sleep(0.1)
            waited += 0.1
        current_value = self.caller.state.current

        # loop until target value is reached or external stop trigger
        while current_value != target_value and not self._stop_thread:
            sleep(interval_time)
            if abs(current_value - target_value) < 5:
                current_value = target_value
            else:
                if current_value < target_value:
                    current_value += 5
                else:
                    current_value -= 5
            self.set_pwm(current_value)
            if start_delay and current_value == 0 and target_value == 0:
                # if start_delay > 0 assume manual dimming,
                # set target to 100 for bidirectional dimming
                target_value = 100

        # save value since its now the current state
        self.caller.state.current = current_value
        self.smooth_change.in_progress = False

class TriacDimmer(Actuator):
    """Allows one triac channel to be dimmed on Waveshare 2CH-Triac-HAT.
    Also supports toggling.
    Documentation for the device is available at:
    https://www.waveshare.com/wiki/2-CH_TRIAC_HAT
    """

    def __init__(self, connections, dev_cfg):
        """ Initialises the I2C subsystem and sets the triac to the InitialState.
            If InitialState is not provided in params it defaults to 0%.

            Parameters:
                - "Channel"               : Triac channel No. 1 or 2
                - "MainsFreq"             : Power grid frequency in Hz 50 or 60, default 50
                - "InitialState"          : PWM duty cycle in % when coming online,
                                            defaults to "0", optional.

            Parameters included in external classes:
                - "SmoothChangeInterval"  : Time steps in seconds between PWM changes
                                            while smoothly switching on or off
                - "DimDelay"              : Delay in seconds befor starting to dim the PWM
                - "DimInterval"           : Time steps in seconds between PWM changes while dimming
                - "ToggleDebounce"        : The interval in seconds during which repeated
                                            toggle commands are ignored
        """
        super().__init__(connections, dev_cfg)

        self.channel = int(dev_cfg["Channel"])
        self.freq = dev_cfg.get("MainsFreq", 50)

        # default state if not configured = 0%
        self.state = SimpleNamespace(current=None, last=None)
        inital_state =  int(dev_cfg.get("InitialState", 0))

        try:
            self.driver = i2c_driver()
            self.driver.set_power_grid_frequency(self.log, self.freq)
            self.driver.set_duty_cycle(self.log, self.channel, inital_state)
        except AttributeError:
            self.log.error("%s could not setup TriacDimmer. "
                           "Ensure that the Triac HAT is correctly installed. "
                           "Switch and jumpers on the HAT should be in position 'B'!",
                           self.name)

        # remember the current output state, set last laste for toggle command
        self.state.current = inital_state
        if inital_state == 0:
            self.state.last = 100
        else:
            self.state.last = inital_state

        # define callback method for smooth dimmer thread
        def set_pwm_value(value):
            self.driver.set_duty_cycle(self.log, self.channel, value)
        # read settings for the dimmer options, create instance of _SmoothDimmer
        self.dimmer = _SmoothDimmer(caller = self, callback_set_pwm = set_pwm_value)
        self.debounce = Debounce(dev_cfg, default_debounce_time = 0.15)

        self.log.info("Configued TriacDimmer %s: channel %d, mains frequency %dHz, PWM %s%%",
                      self.name, self.channel, self.freq, inital_state)
        self.log.debug("%s has following configured connections: \n%s",
                       self.name, yaml.dump(self.comm))

        # publish inital state back to remote connections
        self.publish_actuator_state()

        configure_device_channel(self.comm, is_output=False,
                                 name="set duty cycle", datatype=ChanType.INTEGER,
                                 unit="%", restrictions="0:100")
        # The actuator gets registered twice, at core-actuator and here.
        # Currently this is the only way to pass the device_channel_config to homie_conn
        self._register(self.comm, None)

    def on_message(self, msg):
        """Called when the actuator receives a message.
        Sets the triac according to the message value
        """
        self.log.debug("%s triac channel %d received command %s",
                           self.name, self.channel, msg)

        if msg.isdigit():
            # msg contrains digits convert it from string to int
            value = int(msg)
        elif msg == "ON":
            # handle openHab item sending ON
            value = 100
        elif msg == "OFF":
            # handle openHab item sending OFF
            value = 0
        elif msg == "DIM":
            self.dimmer.start_dimming()
            return
        elif msg == "STOP":
            current_state = self.dimmer.stop_dimming()
            if current_state is not None:
                # remember current state
                self.state.current = current_state
                self.log.info("%s dimmed triac channel %d to PWM %d%%",
                              self.name, self.channel, self.state.current)
                self.publish_actuator_state()

            return
        elif is_toggle_cmd(msg):
            if self.debounce.is_within_debounce_time():
                # filter close toggle commands to make sure no double switching occures
                self.log.info("%s triac channel %d received toggle command %s"
                              " within debounce time. Ignoring command!",
                             self.name, self.channel, msg)
                return
            # invert current state on toggle command
            if self.state.current > 0:
                value = 0
            else:
                value = self.state.last
            # remeber last value for later if not zero
            if self.state.current:
                self.state.last = self.state.current
        else:
            # if command is not recognized ignor it
            self.log.warning("%s  triac channel %d received unrecognized command %s",
                             self.name, self.channel, msg)
            return

        # do nothing when the command (value) equals the current state
        if self.state.current == value:
            self.log.info("%s triac channel %d received setpoint %d%%"
                          " which is equal to current PWM value. Ignoring command!",
                          self.name, self.channel, value)
            return

        self.log.info("%s set triac channel %d to PWM %d%%",
                      self.name, self.channel, value)

        self.dimmer.apply_value_change(value)

        self.state.current = value
        self.publish_actuator_state()


    def publish_actuator_state(self):
        """Publishes the current state of the actuator."""
        # openHab only likes string messages, so convert the int
        msg = str(self.state.current)
        self._publish(msg, self.comm)
