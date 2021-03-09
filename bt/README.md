# Bluetooth

This module contains four bluetooth sensors.

## `btle_sensor.btle_sensor.BtleSensor`

A Polling Sensor that listens for BTLE broadcasts from devices with a given BT address for a short time on each poll.
When a packet for a device of interest is received during that period, the ON value is pblished to the destination assocaited with the device address.
When no packet is received for a device of interest, the OFF value is published.

### Dependencies

This sensor uses [`bluepy`](https://github.com/IanHarvey/bluepy) to receive and parse the BTLE packets.

```
$ sudo apt-get install libglib2.0-dev bluetooth
$ sudo pip3 install bluepy
```

Requires sensor_reporter to be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.btle_sensor.BtleSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | A number in seconds, greater than `Timeout` | How often to poll for broadcasts
`Timeout` | X | A number in seconds | How long to listen for BTLE packets during a single poll.
`AddressX` | X | BT MAC address format (i.e XX:XX:XX:XX:XX:XX), letters should be lower case  | The MAC address of a device to listen for boadcasts from. X must be a number starting from 1 and each subsequent address must be sequential in numbering.
`DestinationX` | X | | Destination to publish ON/OFF for the assocaited Address
`Values` | | Two strings separated by a comma (e.g. `OPEN,CLOSED`) | The values to publish. The first value is published when present and the second when not present. Deafults to `ON,OFF`.


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
Class = bluetooth.btle_sensor.BtleSensor
Poll = 10
Connection = openHAB
Timeout = 9
Address1 = aa:bb:cc:dd:ee:ff
Destination1 = dev1
Address2 = 11:22:33:44:55:66
Destination2 = dev2
Address3 = 77:88:99:aa:bb:cc
Destination3 = dev3
Values = ON,OFF
Level = DEBUG
```

## `bt.btscan_sensor.SimpleBtSensor`

A Polling Sensor that polls BT devices by MAC address to determine if they are present or not.

Look at the PyBluez examples for `inquiry.py` for a script that can be used to discover the MAC address of a device.
Run the script and put the device into pairing mode and the MAC address and device name will be printed out.

### Dependencies

The sensor uses [PyBluez](https://github.com/pybluez/pybluez) to scan for BT devices.

```
$ sudo apt-get install bluetooth bluez python3-bluez
```

sensor_reporter must be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.btle_sensor.SimpleBtSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | A number in seconds, greater than 25 | How often to poll for devices, blocks for 25 seconds.
`Address` | X | BT MAC address format (i.e XX:XX:XX:XX:XX:XX), letters should be lower case  | The MAC address of a device to scan for it's presence.
`Destination` | X | | Where to publishs ON/OFF to when the device is found or not.

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
Class = bt.btscan_sensor.SimpleBtSensor
Poll = 26
Connection = openHAB
Address = aa:bb:cc:dd:ee:ff
Destination = dev1
Level = DEBUG

[Sensor2]
Class = bt.btscan_sensor.SimpleBtSensor
Poll = 26
Connection = openHAB
Address = 11:22:33:44:55:66
Destination = dev1
Level = DEBUG
```

## `bt.btscan_sensor.BtRssiSensor` [DEPRECATED]

Similar to the SimpleBtSensor but instead of a simple "present/absent" decision based on whether or not the device was found, it collects the RSSI for packets of devices on each poll.
When a packet above a certain RSSI is received if adds to a near count and subtracts from a far count.
When no packet is received the far count is intremented and near count is decremented.
When the far count exceeds the near count and a threshold count ON is published.
When the near count exceeds the far count and a threshold count OFF is published.

I rewrote this sensor using the `inquiry-with-rssi.py` example from PyBluez but there are better approaches and better products on the market to solve this problem (e.g. https://www.reelyactive.com/).
I do not intend to update this sensor in the future and if there is a problem and someone doesn't submit a PR themselves to fix it, I will remove this sensor.
Frankly, it never really worked well in the first place for device presence detection.

### Dependencies

This sensor uses [`bluepy`](https://github.com/IanHarvey/bluepy) to receive and parse the BTLE packets.

```
$ sudo apt-get install libglib2.0-dev bluetooth
$ sudo pip3 install bluepy
```

Requires sensor_reporter to be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `btle_sensor.btle_sensor.BtRssiSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | A number in seconds, greater than 10 | How often to poll for devices, blocks for 25 seconds.
`Address` | X | BT MAC address format (i.e XX:XX:XX:XX:XX:XX), letters should be lower case  | The MAC address of a device to scan for it's presence.
`Destination` | X | | Where to publishs ON/OFF to when the device is found or not.
`Max` | X | Must be greater than `Near` and `Far`. | The maximum for the near and far counts.
`Far` | X | Must be greater than 0. | The number of far counts threshold.
`Near` | X | Must be greater than 0. | The number of near counds threshold.

### Example Config

```
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
Class = bt.btscan_sensor.BtRssiSensor
Poll = 26
Connection = openHAB
Level = DEBUG
Address = aa:bb:cc:dd:ee:ff
Destination = dev1
Max = 10
Near = 5
Far = 5
Level = DEBUG

[Sensor2]
Class = bt.btscan_sensor.BtRssiSensor
Poll = 26
Connection = openHAB
Address = 11:22:33:44:55:66
Destination = dev2
Max = 8
Near = 2
Far = 3
Level = DEBUG
```

## `govee.govee_sensor.GoveeSensor`

A Background Sensor that listens for and parses BTLE packets from Govee H5075 temperature and humidity sensors, publishing the readings and device status information.

### Dependencies

This sensor is uses the [bleson library](https://github.com/TheCellule/python-bleson) to listen for and parse the packets.

```
$ sudo pip3 install bleson
```

sensor_reporter must be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `bt.govee_sensor.GoveeSensor` |
`Connection` | X | Comma separated list of Connections | Where the ON/OFF messages are published.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Destination` | X | | The root destination to publish to. NOTE: Not currently compatible with the openHAB Connection.

The `Destination` parameter defines the root of the destination hierarcy to publish to.
Each reading is published under that.

Destination | Value
-|-
`<Destination>/<name>/battery` | integer between 0 and 100 representing the battery charge
`<Destination>/<name>/rssi` | integer betweeo 0 and -100 representing the signal strength
`<Destination>/<name>/temp_c` | temp in C to one decimal place
`<Destination>/<name>/temp_f` | temp in F to one decimal place
`<Destination>/<name>/humi` | humidity in percent to one decimal place

where `<Destination>` is the value from the `Destination` parameter and `<name>` is the self reported name of the device.
The name will take the form of `GVH5072_[last 4 digits of address]`.
For example, if the address were `01:23:45:67:89:01` the name would be `GV5072_8901`.

### Example Config

```ini
[Logging]
Syslog = YES
Level = INFO

[Connection1]
Class = mqtt.mqtt_conn.MqttConnection
Name = MQTT
Client = test
User = user
Password = password
Host = localhost
Port = 1883
Keepalive = 10
RootTopic = sensor_reporter
TLS = NO
Level = DEBUG

[Sensor0]
Class = govee.govee_sensor.GoveeSensor
Destination = govee
Connection = MQTT
Level = INFO
```

Given the above configuration, the battery level would be reported to `sensor_reporter/govee/GV_5072_[XX]/battery` where `[XX]` is the last four of each device's address.
