# Sensors and Actuators that are controlled via i2c

This module contains:
* [i2c.relay.EightRelayHAT](#i2crelayeightrelayhat)
* [i2c.triac.TriacDimmer](#i2ctriactriacdimmer)



## `i2c.relay.EightRelayHAT`

Commands a [Sequent Microsystems 8-Relays-HAT](https://github.com/SequentMicrosystems/8relind-rpi) to switch a relay or if configured with SimulateButton it switches ON for half a second and then goes OFF.
A received command will be sent back on all configured connections to the configured return topic, to keep them up to date.

### Dependencies

This actuator communicates via the i2c interface, therfore the GPIO 2 and 3 should be free and cannot get accessed directly e. g. with a RpiGPIOSensor.
Also the library `lib8relay` must be installed to make this actuator work.

To enable the i2c interface open the Raspberry-Pi configuration via:

```bash
sudo raspi-config
```
and choose Interface Options, then <b>I2C Interface</b> and yes.

The user running sensor_reporter must have permission to access the i2c interface.
To grant the `sensorReporter` user i2c permissions add the user to the group `i2c`:

```bash
sudo adduser sensorReporter i2c
```

Install `lib8relay` via:

```bash
sudo pip3 install lib8relay
```

### Parameters

| Parameter        | Required | Restrictions                    | Purpose                                                                                                                                                                                                                                                                       |
|------------------|----------|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`          | X        | `i2c.relay.EightRelayHAT`       |                                                                                                                                                                                                                                                                               |
| `Connections`    | X        | dictionary of connectors        | Defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.                                                                                             |
| `Stack`          |          | Stack Address 0..7              | Optional, the selected stack adress which can be set via jumpers on the header 0-1-2 (no jumper: Stack =  0, default = 0, see product description [here](https://sequentmicrosystems.com/collections/industrial-automation/products/8-relays-stackable-card-for-raspberry-pi))|
| `Relay`          | X        | Relay No. 1..8                  | The relay to control                                                                                                                                                                                                                                                          |
| `Level`          |          | DEBUG, INFO, WARNING, ERROR     | Override the global log level and use another one for this sensor.                                                                                                                                                                                                            |
| `ToggleDebounce` |          | decimal number                  | The interval in seconds during which repeated toggle commands are ignored (default 0.15 seconds)                                                                                                                                                                              |
| `InitialState`   |          | ON or OFF                       | Optional, when set to ON the pin's state is initialized to HIGH. Ignores InvertOut (default OFF)                                                                                                                                                                              |
| `SimulateButton` |          | Boolean                         | When `True` simulates a button press by setting the pin to HIGH for half a second and then back to LOW. In case of `InitalState` ON it will toggle the other way around.                                                                                                      |




### Outputs / Inputs

The EightRelayHAT has only one output and input.
The input expects ON, OFF, TOGGLE or a datetime string as command.
While ON, OFF set the relay accordingly, TOGGLE and a datetime string will toggle it.
Can be connected directly to a RpiGpioSensor ShortButtonPress / LongButtonPress output.
The output will send the relay state as ON / OFF after a change.
When using with the openHAB connection configure a switch/string Item.

### Hardware address

The 8-Relays-HAT uses internally the i2c addresses from 56 to 63 or 32 to 39 depending on the hardware version (hexadecimal from 0x38 to 0x3F or 0x20 to 0x27).
This address can be configured with jumpers see [here](https://sequentmicrosystems.com/collections/industrial-automation/products/8-relays-stackable-card-for-raspberry-pi).
Stack 0 equals address (decimal) 56 or 32, stack 7 equals (decimal) 63 or 39.
No other i2c devices with the same address can be installed at the same time.

### Configuration Examples

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

ActuatorGarageDoor:
    Class: i2c.relay.EightRelayHAT
    Connections:
        openHAB:
            Item: GarageDoorCmd
    Relay: 1
```

## `i2c.triac.TriacDimmer`

Commands a [Waveshare 2-Ch Triac HAT](https://www.waveshare.com/wiki/2-CH_TRIAC_HAT) to set the Triac PWM.
A received command will be sent back on all configured connections to the configured return topic, to keep them up to date.

### Dependencies

This actuator communicates via the i2c interface, therfore the GPIO 2 and 3 should be free and cannot get accessed directly e. g. with a RpiGPIOSensor.
Also the library `smbus2` must be installed to make this actuator work.

To enable the i2c interface open the Raspberry-Pi configuration via:

```bash
sudo raspi-config
```
and choose Interface Options, then <b>I2C Interface</b> and yes.

The user running sensor_reporter must have permission to access the i2c interface.
To grant the `sensorReporter` user i2c permissions add the user to the group `i2c`:

```bash
sudo adduser sensorReporter i2c
```

Install `smbus2` via:

```bash
sudo pip3 install smbus2
```

### Parameters

| Parameter              | Required | Restrictions                    | Purpose                                                                                                                                                                              |
|------------------------|----------|---------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`                | X        | `i2c.triac.TriacDimmer`         |                                                                                                                                                                                      |
| `Connections`          | X        | dictionary of connectors        | Defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.    |
| `Channel`              | X        | triac channel No. 1 or 2        | The triac channel to control                                                                                                                                                         |
| `MainsFreq`            |          | frequency in Hz 50 or 60        | The Power grid frequency in Herz 50 or 60, default 50                                                                                                                                |
| `Level`                |          | DEBUG, INFO, WARNING, ERROR     | Override the global log level and use another one for this sensor.                                                                                                                   |
| `ToggleDebounce`       |          | decimal number                  | The interval in seconds during which repeated toggle commands are ignored. (default 0.15 seconds)                                                                                    |
| `InitialState`         |          | integer                         | When set the triac PWM is initialized to the given duty cycle in percent. (default 0)                                                                                                |
| `SmoothChangeInterval` |          | decimal number                  | Time steps in seconds between PWM changes while smoothly switching on or off. If the value is 0, there is no smooth change when the setpoint changes. (default 0.05)                 |
| `DimDelay`             |          | decimal number                  | Delay in seconds before manual PWM dimming starts. (default 0.5)                                                                                                                     |
| `DimInterval`          |          | decimal number                  | Time steps in seconds between PWM changes during manual dimming. (default 0.2)                                                                                                       |



### Outputs / Inputs

The TriacDimmer has only one output and input.
The input expects a whole number, ON, OFF, DIM, STOP, TOGGLE or a datetime string as a command.
A received number will set the Triac PWM duty cycle accordingly, 0% equals off.
While ON, OFF will set the triac PWM to 100% or 0% respectively, TOGGLE and a datetime string will toggle the PWM to the last state.

If DIM is received manual, dimming will start after `DimDelay` and the PWM will dim every `DimInterval` seconds in 5% steps until the STOP command is sent.
If the current PWM value is greater then zero manual dimming will dim down to 0% and then up to 100%.
Otherwise, if the PWM value is zero, manual dimming will dim up to 100%. 
The STOP command will also interrupt the `DimDelay`, so no manual dimming will occur.

Can be connected directly to a RpiGpioSensor ShortButtonPress / LongButtonPress output.
The output will send the Triac PWM duty cycle as number (0 - 100) after a change.
When using with the openHAB connection configure a dimmer/string Item.

### Hardware address

The 2-Ch Triac HAT uses the i2c address 71 internally (hexadecimal 0x47).
This address is hardcoded into the HAT and cannot be changed.
No other i2c devices with the same address can be installed at the same time.

### Configuration Examples
The following config will toggle the dimmer if the LightPushButton is pressed for less then 0.4 seconds (`Long_Press-Threshold`).
If it is pressed longer than 0.5 seconds (`DimDelay`) the manual dimming will start and stop only when the button is released.

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection_local:
    Class: local.local_conn.LocalConnection
    Name: local

ActuatorLightDimmer:
    Class: i2c.triac.TriacDimmer
    Connections:
        local:
            CommandSrc: dimmer1
    Channel: 1

SensorLightPushButton:
    Class: gpio.rpi_gpio.RpiGpioSensor
    Connections: 
        local:
            Switch:
                StateDest: dimmer1
            ShortButtonPress:
                StateDest: dimmer1
    Pin: 17
    PUD: UP
    EventDetection: BOTH
    Long_Press-Threshold: 0.4
    Values:
        local:
            - 'DIM'
            - 'STOP'
```
