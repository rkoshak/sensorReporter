# Exec

This module has a Polling Sensor and Actuator that executes command line commands on command or via a poll.

## `exec.exec_actuator.ExecActuator`

Subscribes to the given topic for messages.
Any message that is received will cause the command to be executed.
If the message is anything but "NA" the message is treated as command line arguments.
The result is published to the return topic.

### Dependencies

None, though the user that sensor_reporter is running needs permission to execute the command.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `exec.exec_actuator.ExecActuator` |
`Connections` | X | dictionary of connectors | Defines where to subscribe for messages and where to publish the status for each connection. Look at connection readme's for 'Actuator / sensor relatet parameters' for details. When using with the openHAB connection configure a string item at openHAB.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the actuator.
`Command` | X | `;` and `#` are not allowed. | A valid command line command.
`Timeout` | X | The maximum number of seconds to wait for the command to finish.

When the command returns an error, `ERROR` is published.

### Example Config

```yaml
Logging:
    Syslog: yes
    Level: WARNING

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

Actuator1:
    Class: exec.exec_actuator.ExecActuator
    Connections:
        openHAB:
            Item: Test_Act1
    Command: echo
    Timeout: 10
    Level: INFO
```

## `exec.exec_sensor.ExecSensor`

A Polling Sensor that executes a given command and publishes the result.

### Dependencies

None, though the user that sensor_reporter is running needs permission to execute the command.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `exec.exec_sensor.ExecSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number | How often to call the command
`Script` | X | `;` and `#` are not allowed. | A valid command line command.

Note that the command timeout is set to`Poll`.

### Example Config

```yaml
Logging:
    Syslog: yes
    Level: WARNING

Connection1:
    Class: mqtt.mqtt_conn.MqttConnection
    Name: MQTT
    Client: test
    User: user
    Password: password
    Host: localhost
    Port: 1883
    Keepalive: 10
    RootTopic: sensor_reporter

SensorExecEcho:
    Class: exec.exec_sensor.ExecSensor
    Connections:
        MQTT:
            StateDest: hello_world/state
    Poll: 10
    Script: echo Exec hello from sensor 1
    Level: INFO
```
