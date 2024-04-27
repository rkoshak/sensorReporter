# openHAB REST Connection

This Connection provides a two way connection to an openHAB instance.
I uses the REST API to publish Item updates and it subscribes to the SSE feed for Item commands.
Checks connection status every 30 seconds.
Automatically reconnects if necessary.

## Dependencies

Item updates are issue via [requests](https://pypi.org/project/requests/).
Uses [sseclient-py](https://pypi.org/project/sseclient-py/) to subscribe to the SSE feed.

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh openhab_rest
```

## Parameters

| Parameter         | Required | Restrictions                         | Purpose                                                                                                                                                                                                                                                                                         |
|-------------------|----------|--------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Class`           | X        | `openhab_rest.rest_conn.OpenhabREST` |                                                                                                                                                                                                                                                                                                 |
| `Level`           |          | DEBUG, INFO, WARNING, ERROR          | When provided, sets the logging level for the connection.                                                                                                                                                                                                                                       |
| `Name`            | X        | Unique to sensor_reporter            | Name for the connection, used in the list of Connections for Actuators and Sensors.                                                                                                                                                                                                             |
| `URL`             | X        | http / https URL : port              | The base URL and port of the openHAB instance. Example unencrypted: `http://localhost:8080`, example with TLS encryption: `https://localhost:8443`. For the later a Certificate Authority's certificate must be set.                                                                            |
| `RefreshItem`     | X        |                                      | Name of a Switch Item; sending an ON command to the Item will cause sensor_reporter to publish the most recent state of all the sensors.                                                                                                                                                        |
| `openHAB-Version` |          | Float                                | Version of the OpenHAB server to connect to as floating point figure. Default is '2.0'.                                                                                                                                                                                                         |
| `API-Token`       |          |                                      | The API token generated on the [web interface](https://www.openhab.org/docs/configuration/apitokens.html). Only needed if 'settings > API-security > implicit user role (advanced settings)' is disabled. If no API token is specified sensor_reporter tries to connect without authentication. |
| `CAcert`          |          | String                               | Optional path to the Certificate Authority's certificate that signed the openHab certificate. Example: `./certs/ca.crt` Default is no certificate.                                                                                                                                              |
| `TLSinsecure`     |          | Boolean                              | Optional parameter to disable verification of the server hostname in the server certificate. Default is `False`.                                                                                                                                                                               |


### Actuator / sensor relevant parameters

To use an actuator or a sensor (a device) with a connection it has to define this in the device 'Connections:' parameter with a dictionary of connection names and connection related parameters (see Dictionary of connectors layout).
The openHAB REST connection uses following parameters:

| Parameter | Required | Restrictions                    | Purpose                                                                                                                                                                                                                |
|-----------|----------|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Item`    | yes      | Alphanumeric & underscores only | specifies the topic to subscribe for actuator events and the return topic to publish the current device state / sensor reading. Device state is published as item update. Actuators are only triggerd on item commands |

### Dictionary of connectors layout
To configure a openHAB REST connection in a sensor / actuator use following layout:

```yaml
Connections:
    <connection_name>:
        <sensor_output_1>:
            Item: <some Item_name>
        <sensor_output_2>:
            Item: <some Item_name2>
    <connection_name2>:
        #etcetera
```
The available outputs are described at the sensor / actuator readme.

Some sensor / actuators have only a single output / input so the sensor_output section is not neccesary:

```yaml
Connections:
    <connection_name>:
        Item: <some Item_name>
```

#### Trigger disconnect / reconnect actions
This connection supports triggering actions on disconnect / reconnect for actuators and storing sensor readings while the connection is offline and sending them all at once on reconnect for sensors.
These options are configured for each device and are defined within the device's `Connections:` parameter. 

##### Actuator related parameters:
Can be defined within the `ConnectionOnDisconnect:` and `ConnectionOnReconnect:` parameter.

| Parameter         | Required            | Restrictions               | Purpose                                                                                                                                           |
|-------------------|---------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `ChangeState`     |                     | Boolean                    | Trigger actuator state change on disconnect/reconnect (default = no)                                                                              |
| `TargetState`     | if ChangeState: yes | String in single 'quotes'  | The command to send to the actuator when the trigger occurs. Make sure the data type matches the actuator and use single 'quotes'                 |
| `ResumeLastState` |                     | Boolean, only on reconnect | If yes, the actuator will return to the last known state state on reconnection. Only works on actuators with return topic feature (default = no)  |

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
| `SendReadings`     |          | Boolean      | If yes, sensors readings will be collected while connection is offline and send when reconnected (default = no)       |
| `NumberOfReadings` |          | Integer      | Number of readings to be collected. Will be sent in the same order after reconnection, oldest first (default = 1 )    |

```yaml
Connections:
    <connection_name>:
        # sensor topic config omitted
        ConnectionOnDisconnect:
            SendReadings: < yes / no >
            NumberOfReadings: < whole number >
```

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
    openHAB-Version: 3.2
    API-Token: <API-Token generated from openHAB profil page>
    Level: INFO

SensorHeartbeart:
    Class: heartbeat.heartbeat.Heartbeat
    Connections:
       openHAB:
           FormatNumber:
               Item: heartbeat_num
           FormatString:
               Item: heartbeat_str
    Poll: 60
```

## OpenHAB setup
Login in openHAB as Admin and add a new point (settings > model > add point) for every sensor/actor to use with sensor_reporter.
You can add the point straight away to the [semantic model](https://www.openhab.org/docs/tutorial/model.html) of your smart home or do it later.
Obviously the point names in openHAB and in the sensor_reporter config have to be the identical.
Point label can be chosen freely.
The point type vary, see the plugin readme's for more information.

Note: In a setup with a sensor and an actuator with the same label, the actuator will not be triggered by openHAB when an update on the destination happens.
Use a local/mqtt connection for direct sensor/actuator connections.

## Connection encryption
To access the openHAB REST-API with an encrypted connection, configure `URL` with https:// prefix and port 8443.
By default the openHAB server has created a certificate which is unknown to sensor_reporter.
To connect anyway use `TLSinsecure: yes`.
This will skip the certificate validation, i.e. sensor_reporter will not recognize if the server changes and a man in the middle attack would be possible.

To enable certificate validation self signed certificates must be created and installed in openHAB and sensor_reporter. 
1. Create certificates: [this](https://blog.devgenius.io/how-to-generate-self-signed-ssl-certificates-b85562830ab) webside explains this for Linux and Mac
2. Install the server certificate in openHAB following this [guide](https://gist.github.com/DanielDecker/5ab62a55fd9e53d0bfd3d7ffec1a4916)
3. Configure the path to the root certificate in openHAB with `CAcert:`
4. Start sensor_reporter
