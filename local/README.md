# Local

This module contains the local connection (on device) and the local logic actuator:
* [Local-Connection](#local-connection)
* [local.local_logic.LogicOr](#locallocal_logiclogicor)

## Local Connection

The local connection is a powerful way to implement simple autonomous sensor/actuator combinations.
For example:

    - turn on an LED connected to a GPIO pin when a reed sensor connected to another pin is HIGH
    - execute a script when a temperature sensor exceeds 70 degrees F
    - turn on a relay when the humidity sessor exceeds 50%

Any sensor that has the Local Connection listed will publish it's readings to the configured destination.
Any sensor that needs to react to that sensor's reading would also list the Local Connection and will use the same destination.

Local Connection allows some simple less than, greater than,and equals logic.
Toggle events, e.g. from a RpiGpioSensor will get forwarded in any case.

### Parameters

| Parameter | Required | Restrictions                       | Purpose                                                                                    |
|-----------|----------|------------------------------------|--------------------------------------------------------------------------------------------|
| `Class`   | X        | `local.local_conn.LocalConnection` |                                                                                            |
| `Level`   |          | DEBUG, INFO, WARNING, ERROR        | When provided, sets the logging level for the connection.                                  |
| `Name`    | X        | Unique to sensor_reporter          | Name used to reference this connection in Actuators and Sensor's Connection parameter.     |
| `OnEq`    |          | String, use ' '                    | Sends an ON message to the actuator(s) when the sensor value matches this parameter.       |
| `OnGt`    |          | Number                             | Sends an ON message to the actuator(s) when sensor value is greater than this parameter.   |
| `OnLt`    |          | Number                             | Sends an ON message to the actuator(s) when the sensor value is lower than this parameter. |

One of `OnEq`, `OnGt`, or `OnLt` need to be present and `True`.
If more than one is present and `True` the first one marked as `True` is selected in the order listed (e.g. if `OnGt` and `OnLt` are both `True`, `OnGt` will be used and `OnLt` will be ignored).
Toggle events a evaluated before `OnEq`, `OnGt` and `OnLt`.

If none of the three optional parameters are supplied, the recieved messages will get forwarded unchanged.

### Actuator / sensor relevant parameters

To use an actuator or a sensor (a device) with a connection it has to define this in the device 'Connections:' parameter with a dictionary of connection names and connection related parameters (see Dictionary of connectors layout).
The local connection uses following parameters:

| Parameter    | Required          | Restrictions | Purpose                                                                                                                    |
|--------------|-------------------|--------------|----------------------------------------------------------------------------------------------------------------------------|
| `CommandSrc` | yes for actuators |              | specifies the topic to subscribe for actuator events                                                                       |
| `StateDest`  |                   |              | optional return topic to publish the current device state / sensor readings. If not present the state won't get published. |

#### Dictionary of connectors layout
To configure a local connection in a sensor / actuator use following layout:

```yaml
Connections:
    <connection_name>:
        <sensor_output_1>:
            CommandSrc: <some topic>
            StateDest: <some other topic>
        <sensor_output_2>:
            CommandSrc: <some topic
            StateDest: <some other topic2>
    <connection_name2>:
        #etcetera
```
The available outputs are described at the sensor / actuator readme.

Some sensor / actuators have only a single output / input so the sensor_output section is not neccesary:

```yaml
Connections:
    <connection_name>:
        CommandSrc: <some topic>
        StateDest: <some other topic>
```

### Example Configs

#### Turn on an LED on GPIO pin 17 when GPIO pin 4 is HIGH

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection0:
    Class: local.local_conn.LocalConnection
    Level: INFO
    Name: local
    OnEq: 'ON'

SensorGaragePushbutton:
    Class: gpio.rpi_gpio.RpiGpioSensor
    Connections:
        local:
            Switch:
                StateDest: back-door
    Pin: 4
    PUD: UP
    EventDetection: BOTH
    Values:
        local:
            - 'ON'
            - 'OFF'
    Level: DEBUG

ActuatorGaragedoor:
    Class: gpio.rpi_gpio.RpiGpioActuator
    Connections:
        local:
            CommandSrc: back-door
    Pin: 17
    InitialState: OFF
    Toggle: true
    Level: DEBUG
```

#### Execute a Script when Temperatur < 32

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection0:
    Class: local.local_conn.LocalConnection
    Name: local_conn
    OnLt: 32

SensorEnvSensor:
    Class: gpio.dht_sensor.DhtSensor
    Connections:
        local_conn:
            Temperatur:
                StateDest: temperature
            Humidity:
                StateDest: humidity
    Poll: 2
    Sensor: AM2302
    Pin: 1
    TempUnit: F
    Smoothing: False
    Level: DEBUG

ActuatorEcho:
    Class: exec.exec_actuator.ExecActuator
    Connections:
        local_conn:
            CommandSrc: temperature
            StateDest: results
    Command: echo "It's too cold!"
    Timeout: 10
```


## Local logic gate

### `local.local_logic.LogicOr`

Forwards commands from one or several inputs to several local outputs (actuators).
The inputs are combined with a 'or' logic gate.

- If one input is ON the output is ON.
- If all inputs are OFF the output is OFF.
- Toggle commands will toggle the output.

#### Limitations

* Can only forward commands to local connections.
* There can be only one subscription for a named destination per connection. E. g. if the topic `red_light` is used by several actuators (parameter `CommandSrc`, `Item`) only the last one will work.
* The LogicOr can't be used with the homie connector

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `local.local_logic.LogicOr` |
`Connections` | X | dictionary of connectors | defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Values` | | list of strings or dictionary | Values to replace the default state message for all outputs (default is ON, OFF). For details see below.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the actuator.

##### Values parameter
With this parameter the default state messages for all output can be overwrite.
Two different layouts are possible.
To override the state message for all defined connections, configure a list of two string items:

```yaml
Values:
    - 'ON'
    - 'OFF'
```
The fist string will be send if the actuator is ON, the second on OFF.

If separate state messages for each connection are desired, configure a dictionary of connection names containing the string item list:

```yaml
Values:
    <connection_name>:
        - 'ON'
        - 'OFF'
    <connection_name2>:
        - 'high'
        - 'low'
```
If a configured connection is not present in the Values parameter it will use the sensor default state messages (ON, OFF).

#### Outputs / Inputs
The LogicOr has 2 inputs and one output which can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).

Output / Input | Purpose
-|-
`Enable` | Input to disable the LogicOr. Expects as command ON / OFF. The LogicOr is enabled by default.
`Input` | Input for controlling the output. Expects a list of items (one in each line) using the connection related Paramater name (e. g. `CommandSrc` for local connections). Expects ON / OFF / TOGGLE.
`Output` | Output: list of command recievers (one in each line). Only local actuators can be triggerd. Will forward the command ON / OFF or what is specified at `Values`

#### Example Config

```yaml
DEFAULT:
    #set common parameters
    PUD: UP
    Poll: 1
    Values:
        - 'ON'
        - 'OFF'

Logging:
    Syslog: yes
    Level: INFO

Connection0:
    Class: local.local_conn.LocalConnection
    Name: local
    OnEq: 'ON'

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

SensorMotinoDetector1:
    Class: gpio.rpi_gpio.RpiGpioSensor
    Connections:
        local:
            Switch:
                StateDest: motion1
    Pin: 17

SensorMotinoDetector2:
    Class: gpio.rpi_gpio.RpiGpioSensor
    Connections:
        local:
            Switch:
                StateDest: motion2
    Pin: 18


Actuator_led0:
    Class: gpio.rpi_gpio.RpiGpioActuator
    Connections:
        local:
            CommandSrc: red_light
    Pin: 35

Actuator_led1:
    Class: gpio.rpi_gpio.RpiGpioActuator
    Connections:
        local:
            CommandSrc: blue_light
    Pin: 19

ActuatorOR:
    Class: local.local_logic.LogicOr
    Connections:
        local:
            Input:
                CommandSrc:
                    - motion1
                    - motion2
            Output:
                StateDest:
                    - red_light
                    - blue_light
        openHAB:
            Input:
                Item:
                    - openhab_sw1
            Enable:
                Item: enable_or
```
In the above example both lights get switched on if either `motion1`, `motion2` or a remote openhab switch `openhab_sw1` sends the command ON. 
An openHAB item called `enable_or` can send the command OFF, to disable the LogicOr.
