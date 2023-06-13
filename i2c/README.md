# Sensors and Actuators that are controlled via i2c

This module contains:
* [i2c.relay.EightRelayHAT](#i2crelayeightrelayhat)



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
    Stack: 0
    Relay: 1
    SimulateButton: True
```


