# Network Sensors

Sensors that operate at the network level including an ARP table scanner and an Amazon Dash Button detector.

## `network.arp_sensor.ArpSensor`

A simple Polling Sensor that periodically pulls the ARP table using a terminal command and parses out the MAC addresses for as address of interest.

### Dependencies

The `arp` command must be installed.

```
$ sudo apt install net-tools
```

The user sensor_reporter is running under must have permission to run the arp command.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `network.arp_sensor.ArpSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X |  Positive number | How often to pull the ARP table.
`MAC` | X | Networking MAC address, lowercase letters | The device to look for in the table.

### Output
The ArpSensor has only one output.
Will send ON then the divice is present and OFF when not.
When using with the openHAB connection configure a switch/string item.

### Example Config

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

SensorArpMyPhone:
    Class: network.arp_sensor.ArpSensor
    Poll: 10
    Connections:
        openHAB:
            Item: my_phone
    MAC: aa:bb:cc:dd:ee:ff
    Level: DEBUG
```

## `network.dash_sensor.DashSensor`

A Background Sensor that sniffs for ARP packets from a given device from given Dash buttons.
It should be usable to detect any device first comming online on a network.

To find the MAC address of your Dash buttons, run `sudo python3 getMac.py` and press the button.
The script will print out the MAC address of the button.

### Dependencies

Must be run as root in order to go into sniffing mode.

Uses [Scapy](https://pypi.org/project/scapy/) to do network sniffing. Scrapy depends on libpcap.

```
$ sudo pip3 install scapy
$ sudo apt install libpcap0.8
```

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `network.dash_sensor.DashSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`MACX` | X | Networking MAC address, lower case letters. | The MAC address of the device to watch for. `X` is a number starting with 1 and incrementing to list more than one device.

### Outputs
The DashSensor can have 1 or many outputs depending on how many MAC addresses are defined. These can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).
Will send the associated MAC address.
When using with the openHAB connection configure a string item.

Output | Purpose
-|-
`DestinationX` | Where to send the associated MAC address. `X` is a number starting with 1 and incrementing to list more than one device.



### Example Config

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection1:
    Class: openhab_rest.rest_conn.OpenhabREST
    Name: openHAB
    URL: http://localhost:8080
    RefreshItem: Test_Refresh

SensorDashDetector:
    Class: network.dash_sensor.DashSensor
    Connections:
        openHAB:
            Destination1:
                Item: bounty
            Destination2:
                Item: tide
    MAC1: aa:bb:cc:dd:ee:ff
    MAC2: 00:11:22:33:44:55
    Level: DEBUG
```
