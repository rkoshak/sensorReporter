# openHAB REST Connection

This Connection provides a two way connection to an openHAB instance.
I uses the REST API to publish Item updates and it subscribes to the SSE feed for Item commands.

## Dependencies

Uses [requests](https://pypi.org/project/requests/) to issue the Item updates.

Uses [sseclient-py](https://pypi.org/project/sseclient-py/) to subscribe to the SSE feed.

```
$ sudo pip3 install requests
$ sudo pip3 install sseclient-py
```

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `openhab_rest.rest_conn.OpenhabREST` |
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the connection.
`Name` | X | | Unique to sensor_reporter | Name for the connection, used in the list of Connections for Actuators and Sensors.
`URL` | X | http URL | The base URL and port of the openHAB instance.
`RefreshItem` | X | | Name of a Switch Item; sending an ON command to the Item will cause sensor_reporter to publish the most recent state of all the sensors.

## Example Configs

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
Class = heartbeat.heartbeat.Heartbeat
Connection = openHAB
Poll = 60
Num-Dest = heartbeat/num
Str-Dest = heartbeat/str
Level = INFO
```

To detect when a sensor_reporter goes offline, use the Heartbeat and a timer in openHAB to detect when the heartbeat stops.
