# Exec

This module has a Polling Sensor and Actuator that executes command line commands on command or via a poll.

## `exec.exec_actuator.ExecActuator`

Subscribes to the given `CommandSrc` for messages.
Any message that is received will cause the command to be executed.
If the message is anything but "NA" the message is treated as command line arguments.
The result is published to `ResultsDest`.

### Dependencies

None, though the user that sensor_reporter is running needs permission to execute the command.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.exec_actuator.ExecActuator` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the actuator.
`Command` | X | `;` and `#` are not allowed. | A valid command line command.
`CommandSrc` | X | The Communicator destination/openHAB string/switch/integer item to listen to for incoming commands.
`ResultsDest` | X | The Communicator destination/openHAB string item to publish the output/stdout of the command.
`Timeout` | X | The maximum number of seconds to wait for the command to finish.

When the command returns an error, `ERROR` is published.

### Example Config

```ini
[Logging]
Syslog = YES
Level = INFO


[Connection1]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh
Level = INFO

[Actuator1]
Class = exec.exec_actuator.ExecActuator
Connection = openHAB
Command = echo
CommandSrc = Test_Act1
ResultsDest = Test_Act1_Results
Timeout = 10
Level = INFO
```

## `exec.exec_sensor.ExecSensor`

A Polling Sensor that executes a given command and publishes the result.

### Dependencies

None, though the user that sensor_reporter is running needs permission to execute the command.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.exec_actuator.ExecSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number | How often to call the command
`Script` | X | `;` and `#` are not allowed. | A valid command line command.
`Destination` | X | Where to publish the results of the command on each poll.

Note that the command timeout is set to`Poll`.

### Example Config

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection1]
Class = openhab_rest.rest_conn.OpenhabREST
Name = openHAB
URL = http://localhost:8080
RefreshItem = Test_Refresh
Level = INFO

[Sensor1]
class = exec.exec_sensor.ExecSensor
Connection = openHAB
Poll = 10
Script = echo Exec hello from sensor 1
Destination = Hellow
Level = INFO
```
