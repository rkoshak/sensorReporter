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
`openHAB-Version` | | float | Version of the OpenHAB server to connect to as floating point figure. Default is '2.0'.
`API-Token` | | | The API token generated on the [web interface](https://www.openhab.org/docs/configuration/apitokens.html). Only needed if 'settings > API-security > implicit user role (advanced settings)' is disabled. If no API token is specified sensor_reporter tries to connect without authentication.

### Actuator / sensor relatet parameters

To use an actuator or a sensor (a device) with a connection it has to define this in the devices 'Connections:' parameter with a dictionary of connection names and connection related parameters.
The openHAB REST connection uses following parameters:

Parameter | Required | Restrictions | Purpose
-|-|-|-
`Item` | yes | Alphanumeric & underscores only | specifies the topic to subscribe for actuator events and the return topic to publish the current device state / sensor reading. Device state is published as item update. Actuators are only triggerd on item commands

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
           Item: heartbeat_num
    HeartbeartStrConns:
       openHAB:
           Item: heartbeat_str
    Poll: 60
```

To detect when a sensor_reporter goes offline, use the Heartbeat and a timer in openHAB to detect when the heartbeat stops.

This connection has a passive disconnect detection.
Whenever a message to openHAB is send the reception of the message is checked.
If there is no message reception detected eg. after the restart of openHAB, sensor_reporter will automatically reconnect.
To make full use of this feature a Heartbeat every 60s is recommended.


## OpenHAB Setup
Login in openHAB as Admin and add a new point (settings > model > add point) for every sensor/actor to use with sensor_reporter.
You can add the point straight away to the [semantic model](https://www.openhab.org/docs/tutorial/model.html) of your smart home or do it later.
Obviously the point names in openHAB and in the sensor_reporter config have to be the identical.
Point lable can be chosen freely.
The point type vary, see the plugin readme's for more information.

Note: on a setup with an sensor and an actuator with the same destination, the actuator will not get triggered thru openHAB when an update on the destination happens. Use a local/mqtt connection for direct sensor actuator connections.