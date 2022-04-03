# Local Connection

The local connection is a powerful way to implement simple autonomous sensor/actuator combinations.
For example:

    - turn on an LED connected to a GPIO pin when a reed sensor connected to another pin is HIGH
    - execute a script when a temperature sensor exceeds 70 degrees F
    - turn on a relay when the humidity sessor exceeds 50%

Any sensor that has the Local Connection listed will publish it's readings to the configured destination.
Any sensor that needs to react to that sensor's reading would also list the Local Connection and will use the same destination.

Local Connection allows some simple less than, greater than,and equals logic.
Toggle events, e.g. from a RpiGpioSensor will get forwarded in any case.

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `local.local_conn.LocalConnection` |
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the connection.
`Name` | X | | Name used to reference this connection in Actuators and Sensor's Connection parameter.
`OnEq` | | | Sends an ON message to the actuator(s) when the sensor value matches this parameter.
`OnGt` | | Number | Sends an ON message to the actuator(s) when sensor value is greater than this parameter.
`OnLt` | | Number | Sends an ON message to the actuator(s) when the sensor value is lower than this parameter.

One of `OnEq`, `OnGt`, or `OnLt` need to be present and `True`.
If more than one is present and `True` the first one marked as `True` is selected in the order listed (e.g. if `OnGt` and `OnLt` are both `True`, `OnGt` will be used and `OnLt` will be ignored).
Toggle events a evaluated before `OnEq`, `OnGt` and `OnLt`.

If none of the three optional parameters are supplied, the recieved messages will get forwarded unchanged.

## Actuator / sensor relatet parameters

To use an actuator or a sensor (a device) with a connection it has to define this in the device 'Connections:' parameter with a dictionary of connection names and connection related parameters (see Dictionary of connectors layout).
The local connection uses following parameters:

Parameter | Required | Restrictions | Purpose
-|-|-|-
`CommandSrc` | yes for actuators |  | specifies the topic to subscribe for actuator events
`StateDest` |  |  | optional return topic to publish the current device state / sensor readings. If not present the state won't get published.

### Dictionary of connectors layout
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

## Example Configs

### Turn on an LED on GPIO pin 17 when GPIO pin 4 is HIGH

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection0:
    Class: local.local_conn.LocalConnection
    Level: INFO
    Name: local
    OnEq: ON

SensorGaragePushbutton:
    Class: gpio.rpi_gpio.RpiGpioSensor
    Connections:
        local:
            Switch:
                StateDest: back-door
    Pin: 4
    PUD: UP
    EventDetection: BOTH
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

### Execute a Script when Temperatur < 32

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
