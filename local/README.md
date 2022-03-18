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

## Example Configs

### Turn on an LED on GPIO pin 17 when GPIO pin 4 is HIGH

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection0]
Class = local.local_conn.LocalConnection
Level = INFO
Name = local
OnEq = ON

[Sensor0]
Class = gpio.rpi_gpio.RpiGpioSensor
Connection = local
Pin = 4
PUD = UP
EventDetection = BOTH
Destination = back-door
Level = DEBUG

[Actuator0]
Class = gpio.rpi_gpio.RpiGpioActuator
Connection = loacl
CommandSrc = back-door
Pin = 17
InitialState = OFF
Toggle = True
Level = DEBUG
```

### Execute a Script when Temp > 32

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection0]
Class = local.local_conn.LocalConnection
Level = INFO
Name = local
OnLt = 32

[Sensor0]
Class = gpio.dht_sensor.DhtSensor
Connection = openHAB
Poll = 2
Sensor = AM2302
Pin = 1
HumiDest = humidity
TempDest = temperature
TempUnit = F
Smoothing = False
Level = DEBUG

[Actuator0]
Class = exec.exec_actuator.ExecActuator
Connection = openHAB
Command = echo "It's too cold!"
CommandSrc = temperature
ResultsDest = results
Timeout = 10
Level = INFO
```
