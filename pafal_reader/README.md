# pafal_reader.pafal_reader.PafalReader

This sensor allows reading out a Pafal 5EC3gr00006 device using a strongly tailored subset of the iec62056 protocol.
It can be used to monitor the by the "smart meter" recoreded exported and imported energy.

## Dependencies

Uses [serial](https://pypi.org/project/pyserial/) to communicate with via the connected serial device

...

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `heartbeat.heartbeat.Heartbeat` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number in seconds | How often to publish the uptime.
`Num-Dest` | X | | Destination to publish the uptime in milliseconds.
`Str-Dest` | X | | Destinationt to pubnlish dd:hh:mm:ss.

## Example Config

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
