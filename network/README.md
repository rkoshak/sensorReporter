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
`Class` | X | `heartbeat.heartbeat.Heartbeat` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X |  Positive number | How often to pull the ARP table.
`MAC` | X | Networking MAC address, lowercase letters | The device to look for in the table.
`Destnation` | X | Where to publish ON when the device is present and OFF when not.

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
Class = network.arp_sensor.ArpSensor
Poll = 10
Connection = openHAB
MAC = aa:bb:cc:dd:ee:ff
Destination = my_phone
Level = DEBUG
```

## `network.dash_sensor.DashSensor`

A Background Sensor that sniffs for ARP packets from a given device from given Dash buttons.
It should be usable to detect any device first comming online on a network.

To find the MAC address of your Dash buttons, run `sudo python3 getMac.py` and press the button.
The script will print out the MAC address of the button.

### Dependencies

Must be run as root in order to go into sniffing mode.

Uses [Scapy](https://pypi.org/project/scapy/) to do network sniffing.

```
$ sudo pip3 install scapy
```

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `heartbeat.heartbeat.Heartbeat` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`MACX` | X | Networking MAC address, lower case letters. | The MAC address of the device to watch for. `X` is a number starting with 1 and incrementing to list more than one device.
`DestinationX` | X | | The matching destination to publish the Dash button detection events to, corresponds with the `MACX` of the same number.

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

[Sensor5]
Class = network.dash_sensor.DashSensor
Connection = openHAB
MAC1 = aa:bb:cc:dd:ee:ff
Destination1 = bounty
MAC2 = 00:11:22:33:44:55
Destination2 = tide
Level = DEBUG
```
