# Roku Address Sensor

For those users who cannot assing a static IP address to their Roku devices, this Polling Sensor will periodically discover all the Rokus on the network, publishing their current IP address to the return topic.

## Dependencies

None

## Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `roku.roku_addr.RokuAddressSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | Positive number in seconds | How often to publish the uptime.

### Output
The RokuAddressSensor can have 1 or many outputs depending on how many Roku devices are present. These can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).
When using with the openHAB connection configure a string item.

Output | Purpose
-|-
`<Roku device name>` | Where to publish the device IP. Get / set your device names from the [Roku account settings](https://support.roku.com/article/115015821707).

## Example Configs

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

SensorDiscoverRoku:
    Class: roku.roku_addr.RokuAddressSensor
    Connections:
        openHAB:
            Roku remote:
                Item: r_remote
            Roku TV:
                Item: r_tv
    Poll: 30
```
