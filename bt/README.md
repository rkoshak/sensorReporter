# Bluetooth

This module contains three bluetooth sensors:
* [bt.btle_sensor.BtleSensor](#btbtle_sensorbtlesensor)
* [bt.btscan_sensor.SimpleBtSensor](#btbtscan_sensorsimplebtsensor)
* [bt.govee_sensor.GoveeSensor](#btgovee_sensorgoveesensor)

## Find address for Bluetooth device

If the device address is unknown, choose the way to determine it depending on the type of Bluetooth.

### Regular Bluetooth device

Make sure the Bluetooth device is visible (e. g. in pairing mode), then run:

```
hcitool scan
```
The output lists all visible Bluetooth devices as address / name pairs.

### Bluetooth low energie device (BTLE)

Use this method for Bluetooth 4.0 devices.
Make sure the Bluetooth device is active (switched on), then run:

```
sudo hcitool lescan
```
The output will be a address / name pairs for each BTLE message recieved.
After discovering the desired address hit `ctrl + c` to stop the output.

## `bt.btle_sensor.BtleSensor`

A Polling Sensor that listens for BTLE broadcasts from devices with a given BT address for a short time on each poll.
When a packet for a device of interest is received during that period, the ON value is pblished to the destination assocaited with the device address.
When no packet is received for a device of interest, the OFF value is published.

### Dependencies

This sensor uses [`bluepy`](https://github.com/IanHarvey/bluepy) to receive and parse the BTLE packets.
It depends also on the packages `libglib2.0-dev` and `bluetooth`.

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh bt
```

Requires sensor_reporter to be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `bt.btle_sensor.BtleSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | A number in seconds, greater than `Timeout` | How often to poll for broadcasts
`Timeout` | X | A number in seconds | How long to listen for BTLE packets during a single poll.
`AddressX` | X | BT MAC address format (i.e XX:XX:XX:XX:XX:XX), letters should be lower case  | The MAC address of a device to listen for boadcasts from. X must be a number starting from 1 and each subsequent address must be sequential in numbering.
`Values` | | list of strings or dictionary | Values to replace the default state message for all outputs (default is ON, OFF). For details see below.

#### Values parameter
With this parameter the default state messages for all output can be overwrite.
Two different layouts are possible.
To override the state message for all defined connections, configure a list of two string items:

```yaml
Values:
    - 'ON'
    - 'OFF'
```
The fist string will be send if the configured addess is detected, the second if not.

If separate state messages for each connection are desired, configure a dictionary of connection names containing the string item list:

```yaml
Values:
    <connection_name>:
        - 'ON'
        - 'OFF'
    <connection_name2>:
        - 'high'
        - 'low'
```
If a configured connection is not present in the Values parameter it will use the sensor default state messages (ON, OFF).

### Output
The BtleSensor can have 1 or many outputs depending on how many addresses are defined. These can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).
When using with the openHAB connection configure a switch/string item.

Output | Purpose
-|-
`DestinationX` | Where to send send the precence state (default send ON wheb the divice is present and OFF when not). `X` is a number starting with 1 and incrementing to list more than one device.

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

SensorBtleScanner:
    Class: bt.btle_sensor.BtleSensor
    Poll: 10
    Connections:
        openHAB:
            Destination1:
                Item: dev1
            Destination2:
                Item: dev2
            Destination3:
                Item: dev3
    Timeout: 9
    Address1: aa:bb:cc:dd:ee:ff
    Address2: 11:22:33:44:55:66
    Address3: 77:88:99:aa:bb:cc
    Values:
        - present
        - away
    Level: DEBUG
```

## `bt.btscan_sensor.SimpleBtSensor`

A Polling Sensor that polls BT devices by MAC address to determine if they are present or not.

Look at the PyBluez examples for `inquiry.py` for a script that can be used to discover the MAC address of a device.
Run the script and put the device into pairing mode and the MAC address and device name will be printed out.

### Dependencies

The sensor uses [PyBluez](https://github.com/pybluez/pybluez) to scan for BT devices.
It depends also on the packages `bluetooth` and `bluez`

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh bt
```

sensor_reporter must be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `bt.btscan_sensor.SimpleBtSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`Poll` | X | A number in seconds, greater than 25 | How often to poll for devices, blocks for 25 seconds.
`AddressX` | X | BT MAC address format (i.e XX:XX:XX:XX:XX:XX), letters should be lower case  | The MAC address of a device to scan for it's presence. `X` is a number starting with 1 and incrementing to list more than one device.

### Output
The SimpleBtSensor can have 1 or many outputs depending on how many addresses are defined. These can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).
When using with the openHAB connection configure a switch/string item.

Output | Purpose
-|-
`DestinationX` | Where to send send ON then the divice is present and OFF when not. `X` is a number starting with 1 and incrementing to list more than one device.

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

SensorMyPhone:
    Class: bt.btscan_sensor.SimpleBtSensor
    Poll: 26
    Connections:
        openHAB:
            Destination1:
                Item: phone1
            Destination2:
                Item: phone2
    Address1: aa:bb:cc:dd:ee:ff
    Address2: 11:22:33:44:55:66
    Level: DEBUG
```

## `bt.govee_sensor.GoveeSensor`

A Background Sensor that listens for and parses BTLE packets from Govee H5075 temperature and humidity sensors, publishing the readings and device status information.

### Dependencies

This sensor is uses the [bleson library](https://github.com/TheCellule/python-bleson) to listen for and parse the packets.

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh bt
```

sensor_reporter must be run as root.

### Parameters

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Class` | X | `bt.govee_sensor.GoveeSensor` |
`Connections` | X | dictionary of connectors | Defines where to publish the sensor status for each connection. This sensor has 5 outputs, see below. Look at connection readme's for 'Actuator / sensor relevant parameters' for details.
`Level` | | DEBUG, INFO, WARNING, ERROR | When provided, sets the logging level for the sensor.
`TempUnit` | | `F` or `C` | The temperature units. Default is `C`
`Address` | X | BT MAC address format (i.e XX:XX:XX:XX:XX:XX), letters should be lower case  | The MAC address of the Govee H5075 sensor. Should start with "a4:c1:38".

If the address is unknown use the exemple config and check the sensor_reporter log for debug messages with the UUID `GV5072_`

### Outputs
The GoveeSensor has 5 outputs which can be configured within the 'Connections' section (Look at connection readme's for 'Actuator / sensor relevant parameters' for details).

Output | Purpose
-|-
`Temperature` | Where to publish the temperature.
`Humidity` | Where to publish the humidity.
`Battery` | Where to publish the battery charge (integer between 0 and 100)
`RSSI` | Where to publish the signal strength (integer betweeo 0 and -100)
`DeviceName` | Where to publish the self reported name. Usually GVH5072_XXXX

### Example Config

```yaml
Logging:
    Syslog: yes
    Level: INFO

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
    TLS: NO

SensorGoveeKitchen:
    Class: bt.govee_sensor.GoveeSensor
    Connections:
        MQTT:
            Temperature:
                StateDest: govee/temp
            Humidity:
                StateDest: govee/humid
            Battery:
                StateDest: govee/battery
            RSSI:
                StateDest: govee/rssi
            DeviceName:
                StateDest: govee/uuid
    TempUnit: F
    Address: a4:c1:38:00:00:00
    Level: DEBUG
```

Given the above configuration, the battery level would be reported to `sensor_reporter/govee/battery`.
