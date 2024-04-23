# MQTT

This module contains the MQTT and the Homie connection, the later supports auto discover.
* [MQTT-Connection](#mqtt-connection)
* [Homie-Connection](#homie-connection)


## MQTT Connection

A connection to publish and subscribe to MQTT topics.

### Dependencies

MQTT Communication is handled using the [phao-mqtt](https://pypi.org/project/paho-mqtt/) library.

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh mqtt
```

### Parameters

| Parameter     | Required | Restrictions                    | Purpose                                                                                                                                                                                              |
|---------------|----------|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`       | X        | `mqtt.mqtt_conn.MqttConnection` |                                                                                                                                                                                                      |
| `Level`       |          | DEBUG, INFO, WARNING, ERROR     | When provided, sets the logging level for the connection.                                                                                                                                            |
| `Name`        | X        | Unique to sensor_reporter       | Name for the connection, used in the list of Connections for Actuators and Sensors.                                                                                                                  |
| `Client`      | X        | Unique to the broker            | Name used when connecting to the MQTT broker.                                                                                                                                                        |
| `User`        | X        |                                 | MQTT broker login name.                                                                                                                                                                              |
| `Password`    | X        |                                 | Password for the broker login.                                                                                                                                                                       |
| `Host`        | X        |                                 | Hostname or IP address for the MQTT broker.                                                                                                                                                          |
| `Port`        | X        | Integer                         | Port number the MQTT broker is listening on.                                                                                                                                                         |
| `Keepalive`   | X        | Seconds                         | How frequently to exchange keep alive messages with the broker. The smaller the number the faster the broker will detect this client has gone offline but the more network traffic will be consumed. |
| `RootTopic`   | X        | Valid MQTT topic, no wild cards | Serves as the root topic for all the messages published. For example, if an RpiGpioSensor has a destination "back-door", the actual topic published to will be `<RootTopic>/back-door`.              |
| `TLS`         |          | Boolean                         | If set to `True`, will use TLS encryption in the connection to the MQTT broker.                                                                                                                      |
| `CAcert`      |          | String                          | Optional path to the Certificate Authority's certificate that signed the MQTT Broker's certificate. Default is `./certs/ca.crt`.                                                                     |
| `TLSinsecure` |          | Boolean                         | Optional parameter to configure verification of the server hostname in the server certificate. Default is `False`.                                                                                   |

There are two hard coded topics the Connection will use:

- `<RootTopic>/status`: the LWT topic; "ONLINE" will be published when the MQTT connection is established and "OFFLINE" published when disconnecting and as the LWT message.
- `<RootTopic>/refresh`: any message received on this topic will cause the sensor_reporter to immediately publish the most recent sensor readings. Note: it does not actually go out to the device, it only reports the most recent reading.

### Actuator / sensor relevant parameters

To use an actuator or a sensor (a device) with a connection, it has to define this in the device `Connections:` parameter with a dictionary of connection names and connection related parameters (see Dictionary of connectors layout).
The MQTT connection uses following parameters:

| Parameter    | Required          | Restrictions | Purpose                                                                                                           |
|--------------|-------------------|--------------|-------------------------------------------------------------------------------------------------------------------|
| `CommandSrc` | yes for actuators |              | Specifies the topic to subscribe for actuator events                                                              |
| `StateDest`  |                   |              | Return topic to publish the current device state / sensor readings. If not present the state won't get published. |
| `Retain`     |                   | boolean      | If True, MQTT will publish messages with the retain flag. Default is False.                                       |

#### Dictionary of connectors layout
To configure a MQTT connection in a sensor / actuator use following layout:

```yaml
Connections:
    <connection_name>:
        <sensor_output_1>:
            CommandSrc: <some topic>
            StateDest: <some other topic>
        <sensor_output_2>:
            CommandSrc: <some topic
            StateDest: <some other topic2>
            Retain: <as you choose>
    <connection_name2>:
        #etcetera
```
The available outputs are described at the sensor / actuator readme.

Some sensor / actuators have only a single output / input so the sensor_output section is not necessary:

```yaml
Connections:
    <connection_name>:
        CommandSrc: <some topic>
        StateDest: <some other topic>
```

#### Trigger disconnect / reconnect actions
This connection supports triggering actions on disconnect / reconnect for actuators and storing sensor readings while the connection is offline and sending them all at once on reconnect for sensors.
These options are configured for each device and are defined within the device's `Connections:` parameter. 

##### Actuator related parameters:
Can be defined within the `ConnectionOnDisconnect:` and `ConnectionOnReconnect:` parameter.

| Parameter         | Required            | Restrictions               | Purpose                                                                                                                                           |
|-------------------|---------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `ChangeState`     |                     | boolean                    | Trigger actuator state change on disconnect/reconnect (default = no)                                                                              |
| `TargetState`     | if ChangeState: yes | string in single 'quotes'  | The command to send to the actuator when the trigger occurs. Make sure the data type matches the actuator and use single 'quotes'                 |
| `ResumeLastState` |                     | boolean, only on reconnect | If yes, the actuator will return to the last known state state on reconnection. Only works on actuators with return topic feature (default = no)  |

```yaml
Connections:
    <connection_name>:
        # actuator topic config omitted
    	ConnectionOnDisconnect:
    		ChangeState: < yes / no >
    		TargetState: 'ON' 			# some value the actuator supports, could be also '0,0,100' for a  PWM dimmer
    	ConnectionOnReconnect:
    		ChangeState: < yes / no >
    		TargetState: 'OFF'
    		ResumeLastState: < yes / no >
```

##### Sensor related Parameters
Can be defined within the `ConnectionOnDisconnect:` parameter.

| Parameter          | Required | Restrictions | Purpose                                                                                                               |
|--------------------|----------|--------------|---------------------------------------------------------------------------------------------------------------        |
| `SendReadings`     |          | boolean      | If yes, sensors readings will be collected while connection is offline and send when reconnected (default = no)       |
| `NumberOfReadings` |          | Integer      | Number of readings to be collected. Will be sent in the same order after reconnection, oldest first (default = 1 )    |

```yaml
Connections:
    <connection_name>:
        # sensor topic config omitted
        ConnectionOnDisconnect:
            SendReadings: < yes / no >
            NumberOfReadings: < whole number >
```

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
    TLS: no
    Level: DEBUG

SensorGovee:
    Class: govee.govee_sensor.GoveeSensor
    Connections:
        MQTT:
            StateDest: govee
            Retain: yes
    Level: INFO
```

## Homie Connection

A connection to communicate via MQTT using the [Homie convention](https://homieiot.github.io/#), making the sensors and actuators auto discoverable by the home automation software e. g. openHAB.

### Dependencies

MQTT Communication is handled using the [phao-mqtt](https://pypi.org/project/paho-mqtt/) library.
The Homie conventions is implemented via [homie-spec](https://pypi.org/project/homie-spec/).

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh mqtt
```

### Parameters

|   Parameter   | Required | Restrictions                          | Purpose                                                                                                                                                                                              |
|---------------|----------|---------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`       | X        | `mqtt.homie_conn.HomieConnection`     |                                                                                                                                                                                                      |
| `Level`       |          | DEBUG, INFO, WARNING, ERROR           | When provided, sets the logging level for the connection.                                                                                                                                            |
| `Name`        | X        | Unique to sensor_reporter             | Name for the connection, used in the list of Connections for Actuators and Sensors.                                                                                                                  |
| `Client`      |          | Unique to the broker                  | Name used when connecting to the MQTT broker. If not defined the `DeviceID` is used.                                                                                                                 |
| `User`        | X        |                                       | MQTT broker login name.                                                                                                                                                                              |
| `Password`    | X        |                                       | Password for the broker login.                                                                                                                                                                       |
| `Host`        | X        |                                       | Hostname or IP address for the MQTT broker.                                                                                                                                                          |
| `Port`        | X        | Integer                               | Port number the MQTT broker is listening on.                                                                                                                                                         |
| `Keepalive`   | X        | Seconds                               | How frequently to exchange keep alive messages with the broker. The smaller the number the faster the broker will detect this client has gone offline but the more network traffic will be consumed. |
| `DeviceID`    | X        | Unique Homie name, a-z, 0-9, "-", "_" | This name will show up in the auto discover / inbox of the home automation software e. g. openHAB                                                                                                    |
| `TLS`         |          | Boolean                               | If set to `True`, will use TLS encryption in the connection to the MQTT broker.                                                                                                                      |
| `CAcert`      |          | String                                | Optional path to the Certificate Authority's certificate that signed the MQTT Broker's certificate. Default is `./certs/ca.crt`.                                                                     |
| `TLSinsecure` |          | Boolean                               | Optional parameter to configure verification of the server hostname in the server certificate. Default is `False`.                                                                                   |

There are two hard coded topics the Connection will use:

- `connection status`: the LWT topic; "ONLINE" will be published when the MQTT connection is established and "OFFLINE" published when disconnecting and as the LWT message.
- `refresh sensor readings`: any message received on this topic will cause the sensor_reporter to immediately publish the most recent sensor readings. Note: it does not actually go out to the device, it only reports the most recent reading.

### Actuator / sensor relevant parameters

To use an actuator or a sensor (a device) with a connection it has to define this in the device 'Connections:' parameter with a dictionary of connection names and connection related parameters (see Dictionary of connectors layout).
The Homie connection uses following parameters:

| Parameter | Required | Restrictions       | Purpose                                                                                                                                                                                                            |
|-----------|----------|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Name`    | X        | a-Z, 0-9, "-", "_" | Specifies the visible name for the device                                                                                                                                                                          |
| `Type`    |          |                    | Type of the device (homie node, see $type in [Node Attributes](https://homieiot.github.io/specification/#node-attributes)), might change the behavior of the smart home server. (default value is empty string '') |

#### Dictionary of connectors layout
To configure a Homie connection in a sensor / actuator use following layout:

```yaml
Connections:
    <connection_name>:
        Name: <device_name>
```

#### Trigger disconnect / reconnect actions
This connection supports triggering actions on disconnect / reconnect for actuators and storing sensor readings while the connection is offline and sending them all at once on reconnect for sensors.
These options are configured for each device and are defined within the device's `Connections:` parameter. 

##### Actuator related parameters:
Can be defined within the `ConnectionOnDisconnect:` and `ConnectionOnReconnect:` parameter.

| Parameter         | Required            | Restrictions               | Purpose                                                                                                                                           |
|-------------------|---------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `ChangeState`     |                     | boolean                    | Trigger actuator state change on disconnect/reconnect (default = no)                                                                              |
| `TargetState`     | if ChangeState: yes | string in single 'quotes'  | The command to send to the actuator when the trigger occurs. Make sure the data type matches the actuator and use single 'quotes'                 |
| `ResumeLastState` |                     | boolean, only on reconnect | If yes, the actuator will return to the last known state state on reconnection. Only works on actuators with return topic feature (default = no)  |

```yaml
Connections:
    <connection_name>:
        # actuator topic config omitted
        ConnectionOnDisconnect:
            ChangeState: < yes / no >
            # some value the actuator supports, could be also '0,0,100' for a  PWM dimmer
            TargetState: 'ON'
        ConnectionOnReconnect:
            ChangeState: < yes / no >
            TargetState: 'OFF'
            ResumeLastState: < yes / no >
```

##### Sensor related Parameters
Can be defined within the `ConnectionOnDisconnect:` parameter.

| Parameter          | Required | Restrictions | Purpose                                                                                                               |
|--------------------|----------|--------------|---------------------------------------------------------------------------------------------------------------        |
| `SendReadings`     |          | boolean      | If yes, sensors readings will be collected while connection is offline and send when reconnected (default = no)       |
| `NumberOfReadings` |          | Integer      | Number of readings to be collected. Will be sent in the same order after reconnection, oldest first (default = 1 )    |

```yaml
Connections:
    <connection_name>:
        # sensor topic config omitted
        ConnectionOnDisconnect:
            SendReadings: < yes / no >
            NumberOfReadings: < whole number >
```

### Example Config

```yaml
Logging:
    Syslog: yes
    Level: INFO

Connection_homie:
    Class: mqtt.homie_conn.HomieConnection
    Name: homie
    User: user
    Password: password
    Host: localhost
    Port: 1883
    Keepalive: 10
    DeviceID: livingroom

ActuatorExec:
    Class: exec.exec_actuator.ExecActuator
    Connections:
        homie:
            Name: TestAct1
    Command: echo
    Timeout: 10
```
