# Roku Address Sensor

For those users who cannot assing a static IP address to their Roku devices, this Polling Sensor will periodically discover all the Rokus on the network, publishing their current IP address to the destination.

## Dependencies

None

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `roku.roku_addr.RokuAddressSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number in seconds | How often to publish the uptime.

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
Class = roku.roku_addr.RokuAddressSensor
Connection = MQTT
Poll = 30
```
