# heartbeat.heartbeat.Heartbeat

The Heartbeat sensor is a utility to report the sensor_reporter uptime.
This reliable scheduled reporting could be used as a heartbeat and the messages can be used to see how long sensor_reporter has been online.
To detect if sensor_reporter is offline, the linked item on openHAB can use the [expire parameter](https://www.openhab.org/docs/configuration/items.html#parameter-expire), which can be set via 'add metadata > expiration timer' in the item settings. 

## Dependencies

None.

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `heartbeat.heartbeat.Heartbeat` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. This sensor has 2 different outputs, see below. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number in seconds | How often to publish the uptime.

## Outputs
The Heartbeat has 2 outputs which can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).

Output | Purpose
-|-
`FormatNumber` | Destination to publish the uptime in milliseconds. When using with the openHAB connection configure a number item.
`FormatString` | Destination to publish the formated uptime: d 'days,' hh:mm:ss. When using with the openHAB connection configure a string item.

## Example Config

```yaml
Logging:
    Syslog: yes
    Level: INFO

:Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

SensorHeartbeat:
    Class: heartbeat.heartbeat.Heartbeat
    Connections:
        openHAB:
            FormatNumber:
                Item: heartbeat_num
            FormatString:
                Item: heartbeat_str
    Poll: 60
```
