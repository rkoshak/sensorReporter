# Sensors and Actuators that are controlled via i2c

This module contains:
* [i2c.relay.EightRelayHAT](#i2crelayeightrelayhat)
* [i2c.triac.TriacDimmer](#i2ctriactriacdimmer)
* [i2c.pwm.PwmHatColorLED](#i2cpwmpwmhatcolorled)


## `i2c.relay.EightRelayHAT`

Commands a [Sequent Microsystems 8-Relays-HAT](https://github.com/SequentMicrosystems/8relind-rpi) to switch a relay or if configured with SimulateButton it switches ON for half a second and then goes OFF.
A received command will be sent back on all configured connections to the configured return topic, to keep them up to date.

### Dependencies

This actuator communicates via the `i2c interface`, therfore the GPIO 2 and 3 should be free and cannot get accessed directly e. g. with a RpiGPIOSensor.
The user running sensor_reporter must be in the `i2c` group to have access to the i2c interface.
Also the library `lib8relay` must be installed to make this actuator work.

To install the dependencies run (boot partition must be writable): 

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh i2c
```

### Parameters

| Parameter        | Required | Restrictions                    | Purpose                                                                                                                                                                                                                                                                       |
|------------------|----------|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`          | X        | `i2c.relay.EightRelayHAT`       |                                                                                                                                                                                                                                                                               |
| `Connections`    | X        | dictionary of connectors        | Defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.                                                                                             |
| `Stack`          |          | Stack Address 0-7               | Optional, the selected stack adress which can be set via jumpers on the header 0-1-2 (no jumper: Stack =  0, default = 0, see product description [here](https://sequentmicrosystems.com/collections/industrial-automation/products/8-relays-stackable-card-for-raspberry-pi))|
| `Relay`          | X        | Relay No. 1-8                   | The relay to control                                                                                                                                                                                                                                                          |
| `Level`          |          | DEBUG, INFO, WARNING, ERROR     | Override the global log level and use another one for this sensor.                                                                                                                                                                                                            |
| `ToggleDebounce` |          | decimal number                  | The interval in seconds during which repeated toggle commands are ignored (default 0.15 seconds)                                                                                                                                                                              |
| `InitialState`   |          | ON or OFF                       | Optional, when set to ON the pin's state is initialized to HIGH. Ignores InvertOut (default OFF)                                                                                                                                                                              |
| `SimulateButton` |          | Boolean                         | When `True` simulates a button press by setting the pin to HIGH for half a second and then back to LOW. In case of `InitalState` ON it will toggle the other way around.                                                                                                      |
| `InvertOut`      |          | Boolean                         | Inverts the output when set to `True`. If inverted, sending `ON` to the actuator will switch the relay off and `OFF` will switch the relay on (default False).                                                                                                                |

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

Commands a [Waveshare 2-Ch Triac HAT](https://www.waveshare.com/wiki/2-CH_TRIAC_HAT) to set the phase angle control via triac.
A received command will be sent back on all configured connections to the configured return topic, to keep them up to date.

Technical note: The Triac HAT uses forward phase control (FPC), which is suitable for resistive loads.
However, most dimmable power supplies (e.g. for LEDs) require reverse phase control (RPC).

### Dependencies

This actuator communicates via the `i2c interface`, therefore the GPIO 2 and 3 should be free and cannot get accessed directly e. g. with a RpiGPIOSensor.
The user running sensor_reporter must be in the `i2c` group to have access to the i2c interface.
Also the library `smbus2` must be installed to make this actuator work.

To install the dependencies run (boot partition must be writable):

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh i2c
```

### Basic parameters

| Parameter              | Required | Restrictions                    | Purpose                                                                                                                                                                              |
|------------------------|----------|---------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`                | X        | `i2c.triac.TriacDimmer`         |                                                                                                                                                                                      |
| `Connections`          | X        | dictionary of connectors        | Defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.    |
| `Channel`              | X        | triac channel No. 1 or 2        | The triac channel to control                                                                                                                                                         |
| `MainsFreq`            |          | frequency in Hz 50 or 60        | The Power grid frequency in Herz 50 or 60, default 50                                                                                                                                |
| `Level`                |          | DEBUG, INFO, WARNING, ERROR     | Override the global log level and use another one for this sensor.                                                                                                                   |
| `InitialState`         |          | integer                         | When set the forward phase control (FPC) is initialized to the given value in percent. (default 0 = off)                                                                             |

### Advanced parameters

| Parameter              | Required | Restrictions                    | Purpose                                                                                                                                                                              |
|------------------------|----------|---------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `SmoothChangeInterval` |          | decimal number                  | Time steps in seconds between FPC changes while smoothly switching on or off. If the value is 0, there is no smooth change when the setpoint changes. (default 0.05)                 |
| `DimDelay`             |          | decimal number                  | Delay in seconds before manual FPC dimming starts. (default 0.5)                                                                                                                     |
| `DimInterval`          |          | decimal number                  | Time steps in seconds between FPC changes during manual dimming. (default 0.2)                                                                                                       |
| `ToggleDebounce`       |          | decimal number                  | The interval in seconds during which repeated toggle commands are ignored. (default 0.15 seconds)                                                                                    |

### Outputs / Inputs

The TriacDimmer has only one output and input.
The input expects a whole number, ON, OFF, DIM, STOP, TOGGLE or a datetime string as a command.
A received number will set the forward phase control (FPC) accordingly, 0% equals off.
While ON, OFF will set the FPC to 100% or 0% respectively, TOGGLE and a datetime string will toggle the FPC to the last state.

If DIM is received manual, dimming will start after `DimDelay` and the FPC will dim every `DimInterval` seconds in 5% steps until the STOP command is sent.
If the current FPC value is greater then zero manual dimming will dim down to 0% and then up to 100%.
Otherwise, if the FPC value is zero, manual dimming will dim up to 100%. 
The STOP command will also interrupt the `DimDelay`, so no manual dimming will occur.

Can be connected directly to a RpiGpioSensor ShortButtonPress / LongButtonPress output.
The output will send the FPC value as number (0 - 100) after a change.
When using with the openHAB connection configure a dimmer/string Item.

### Hardware address

The 2-Ch Triac HAT uses the i2c address 71 internally (hexadecimal 0x47).
This address is soldered to the underside of the HATs board and cannot be easily changed.
No other i2c devices with the same address can be installed at the same time.

### Configuration Example
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

## `i2c.pwm.PwmHatColorLED`

Commands 1, 3 or 4 channels on the [Adafruit PWM HAT](https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi) to control a white, RGB or RGBW LED.
A received command will be sent back on all configured connections to the configured return topic, to keep them up to date.

### Dependencies

This actuator communicates via the `i2c interface`, therefore the GPIO 2 and 3 should be free and cannot get accessed directly e. g. with a RpiGPIOSensor.
The user running sensor_reporter must be in the `i2c` group to have access to the i2c interface.
Also the library `smbus2` must be installed to make this actuator work.

To install the dependencies run (boot partition must be writable):

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh i2c
```

### Basic parameters

| Parameter       | Required | Restrictions                 | Purpose                                                                                                                                                                                                                                                |
|-----------------|----------|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`         | X        | `i2c.pwm.PwmHatColorLED`     |                                                                                                                                                                                                                                                        |
| `Connections`   | X        | dictionary of connectors     | Defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.                                                                      |
| `Channels`      | X        | dictionary of channels       | Channel to use as PWM output. Use sub-parameter `Red`, `Green`, `Blue`, `White`, with the channel number printed on the HAT (0 to 15). It is not necessary to define pins for all colors.                                                              |
| `Stack`         |          | whole number 0-61            | Stack level of the HAT. Corresponds to the soldered jumpers on the HAT. Board 0 = Stack 0 for details see [here](https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi/stacking-hats#addressing-the-hats-1061336) (default 0). |
| `Level`         |          | DEBUG, INFO, WARNING, ERROR  | When provided, sets the logging level for the sensor.                                                                                                                                                                                                  |
| `InitialState`  |          | dictionary of values 0-100   | Optional, will set the PWM duty cycle for the color (0 = off, 100 = on, full brightness). Use the sub parameter `Red`, `Green`, `Blue`, `White` (default RGBW = 0)                                                                                     |
| `InvertOut`     |          | Boolean                      | Use `True` for common anode LED (default setting). Otherwise use `False`                                                                                                                                                                               |

### Advanced parameters

| Parameter              | Required | Restrictions    | Purpose                                                                                                                                                                     |
|------------------------|----------|-----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PWM-Frequency`        |          | number 30-1600  | Sets the PWM frequency in Hz (default 240 Hz)                                                                                                                               |
| `SmoothChangeInterval` |          | decimal number  | Time steps in seconds between PWM changes while smoothly changing to a new setpoint. If the value is 0, there is no smooth change when the setpoint changes. (default 0.05) |
| `DimDelay`             |          | decimal number  | Delay in seconds before manual brightness dimming starts. (default 0.5)                                                                                                     |
| `DimInterval`          |          | decimal number  | Time steps in seconds between brightness changes during manual dimming. (default 0.2)                                                                                       |
| `ToggleDebounce`       |          | decimal number  | The interval in seconds during which repeated toggle commands are ignored. (default 0.15 seconds)                                                                           |

### Outputs / Inputs
The PwmHatColorLED has only one output and input.
The input expects 3 comma separated values as command. 
The values will set the LED color in HSV color space `h,s,v`, e.g. 240,100,100.
If the white channel is configured and the second value (saturation) = 0 then only the white LED will shine.
If only the white channel is configured one value (0-100) is sufficient as input.
The output will replay the LED color state in the same format.

The PwmHatColorLED also accepts ON, OFF, DIM, STOP, TOGGLE or a datetime string as a command.
While ON, OFF will set the brightness to 100% or 0% respectively, TOGGLE and a datetime string will toggle the brightness to the last state.

If DIM is received manual, dimming will start after `DimDelay` and the brightness will dim every `DimInterval` seconds in 5% steps until the STOP command is sent.
If the current brightness value is greater then zero manual dimming will dim down to 0% and then up to 100%.
Otherwise, if the brightness value is zero, manual dimming will dim up to 100%. 
The STOP command will also interrupt the `DimDelay`, so no manual dimming will occur.

Can be connected directly to a RpiGpioSensor ShortButtonPress / LongButtonPress output.
To use a RpiGpioSensor together with the PwmHatColorLED use the configuration example for the [TriacDimmer](#i2ctriactriacdimmer) above.
When using with the openHAB connection configure a color item.
If only the white channel is configured use a dimmer item in openHAB.

### Hardware address

The PWM HAT uses internally the i2c addresses from 64 to 125 (hexadecimal 0x40 to 7D).
This address can be configured with soldered jumpers see [here](https://learn.adafruit.com/adafruit-16-channel-pwm-servo-hat-for-raspberry-pi/stacking-hats#addressing-the-hats-1061336).
The i2c address equals Stack + 64, e. g. Stack 0 => 0 + 64.
No other i2c devices with the same address can be installed at the same time.

### Configuration Example 1
Control RGBW LED with 4 channels

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection_openHAB:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh
    
ActuatorRgbLED:
    Class: i2c.pwm.PwmHatColorLED
    Channels:
        Red: 0
        Blue: 1
        Green: 2
        White: 3
    InitialState:
        Red: 100
    Connections:
        openHAB:
            Item: eg_w_color_led
```

### Configuration Example 2
Control white LED with 1 channel

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection_openHAB:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh
    
ActuatorWhiteLED:
    Class: i2c.pwm.PwmHatColorLED
    Channels:
        White: 3
    Connections:
        openHAB:
            Item: eg_w_white_pwm
```

## `i2c.aht20.AHT20Sensor`

The `AHT20Sensor` is a polling sensor that reads temperature and humidity from an **AHT20** sensor connected to the Raspberry Pi’s standard **I2C** port (`GPIO 2` for SDA, `GPIO 3` for SCL). 

The sensor operates at a **fixed I2C address (0x38)**, which means multiple AHT20 sensors **cannot** be used on the same I2C bus. 

This implementation has been tested with **Adafruit's [AHT20 breakout board](https://www.adafruit.com/product/4566)**.

### Dependencies

This sensor requires the following libaries:

* adafruit-blinka 
* adafruit-circuitpython-ahtx0

### Parameters

| Parameter     | Required           | Restrictions                            | Purpose                                                                                                                                                     |
|---------------|--------------------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`       | X                  | `i2c.aht20.AHT20Sensor` |                                                                                                                                                             |
| `Connections` | X                  | Dictionary of connectors                | Defines where to publish the sensor status for each connection.                                                                                             |
| `Level`       |                    | `DEBUG`, `INFO`, `WARNING`, `ERROR`     | Override the global log level and use another one for this sensor.                                                                                          |
| `Poll`        | X                  | Positive number                         | Refresh interval for the sensor in seconds.                                                                                                                 |
| `TempUnit`    |                    | `F` or `C`                              | Temperature unit to use, defaults to `C`.                                                                                                                   |
| `Smoothing`   |                    | Boolean                                 | If `True`, publishes the average of the last five readings instead of each individual reading.                                                              |
| `TempDecimals`         |          | Whole number >= 0            | Rounds the temperature output to the given number of decimals using round_half_up logic. Defaults to 3, refelcting the 'resolution ratio' specified in the sensor's technical manual.|
| `HumDecimals`         |          | Whole number >= 0            | Rounds the humidity output to the given number of decimals using round_half_up logic. Defaults to 3, refelcting the 'resolution ratio' specified in the sensor's technical manual.|


### Outputs

Outputs a json string containing the (rounded) values for temperature and relative humidity including the temperature unit. Example:

```json
{
    "temperature": 12.5,
    "temperature_unit": "C",
    "humidity": 65.9
}
```

### Configuration Example

```yaml
# Logging and connection configuration omitted

SensorAHT20:
    Class: i2c.aht20.AHT20Sensor
    Connections:
        MQTT:
            StateDest: temp_hum
    Poll: 10
    TempDecimals: 2
```