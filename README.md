# sensor_reporter
sensor_reporter is a Python 3 script that bridges sensors and actuators to MQTT or openHAB's REST API.
It's a modular script that allows for relatively easy implementation of new capabilities with minimal effort.
If you've used sensorReporter or mqttReporter before, this is a complete rewrite with many breaking changes.
See the release notes below for details.

A number of connections, sensors, and actuators are currently supported.
    - Connection: responsible for publishing sensor readings and actuator results and subscribing for actuator commands.
    - Actuators: classes that perform some action when a message is received.
    - Polling Sensors: classes that query some device on a set polling period.
    - Background Sensors: classes that sense for events in the background and do not require polling.

Go into the subfolders for details in each subfolder's README.

Plug-in | Type | Purpose
-|-|-
`bt.btle_sensor.BtleSensor` | Background Sensor | Scans for BTLE advertisements from configured devices.
`bt.btscan_sensor.SimpleBtSensor` | Polling Sensor | Scans for the presence of BT devices with a given addresses.
`bt.btscan_sensor.BtRssiSensor` | Polling Sensor | Scans for a device with a given address and if it sees it enough reporte it present or absent if it doesn't.
`bt.govee_sensor.GoveeSensor` | Background Sensor | Receives BTLE packets from Govee H5075 temperature and humidity sensors.
`exec.exec_actuator.ExecActuator` | Actuator | On command, executes the configured command line command.
`exec.exec_sensor.ExecSensor` | Polling Sensor | Executes the configured command line and publishes the result.
`gpio.dht_sensor.DhtSensor` | Polling Sensor | Publishes temperature and humidity readings from DHT11, DHT22, and AM2302 sensors connected to GPIO pins.
`gpio.rpi_gpio.RpiGpioSensor` | Polling or Background Sensor | Publsihes ON/OFF messages based on the state of a GPIO pin.
`gpio.rpi_gpio.RpiGpioActuator` | Actuator | Sets a GPIO pin to a given state on command.
`heartbeat.heartbeat.Heartbeat` | Polling Sensor | Publishes the amount of time sensor_reporter has been up as number of msec and as DD:HH:MM:SS.
`local.local_conn.LocalConnection` | Connection | Allows sensors to call actuators.
`mqtt.mqtt_conn.MqttConnection` | Connectioln | Allows Actuators to subscribe and publish and Sensors to publish results.
`network.arp_sensor.ArpSensor` | Polling Sensor | Periodically gets and parses the ARP table for given mac addresses.
`network.dash_sensor.DashSensor` | Background Sensor | Watches for Amazon Dash Button ARP packets.
`openhab_rest.rest_conn.OpenhabREST` | Connection | Subscribes and publishes to openHAB's REST API. Subscription is through openHAB's SSE feed.
`energymeter.read_meter_values.Pafal20ec3gr` | Polling Sensor | Periodically reads out an energymeter using serial device. Currently only Pafal 20ec3gr supported.
`roku.roku_addr.RokuAddressSensor` | Polling Sensor | Periodically requests the addresses of all the Rokus on the subnet.


# Architecture
The main script is `sensor_reporter` which parses a configuration ini file and handles operating system signal handling.

It uses a `core.poll_mgr.PollMgr` manages running a polling loop used by Polling Sensors to control querying the devices.

All connections inherit from `core.connection.Connection`.
All Actuators inherit from `core.actuator.Actuator` and all sensors inherit from `core.sensor.Sensor`.
Common code is implemented in the parent classes.

On startup or when receiving a `HUP` (`kill -1`) operating system signal the configuratuion ini file is loaded.
There is a logging section (see below) where the logging level and where to log to is defined.
Then there is a separate section for each connection, sensor, and actuator.
Each individual plug-in will define it's own set of required and optional parameters.
See the README files in the subfolders for details.

However, some parmeters will be common.
    - All polling sensors require a Poll parameter indicating how often in seconds to poll the sensor devices
    - All sections require a Class parameter defining the class to load.
    - All sensors and actuators require a Connection class containing the name of the Connection to publish/subscribe through. More than one can be defined in a comma separated list.
    - All sections have an optional Level parameter where the logging level for that plugin or sensor_reporter overall can be set. Supported levels are DEBUG, INFO, WARNING, and ERROR.

Sensors are defined in a `[SensorX]` section where `X` is a unique number.
Connections and Actuators are defined in similarly named sections.
The number need only be unique, they don't need to be sequential.

# Dependencies
sensor_reporter only runs in Python 3 and has only been tested in Python 3.7.
Each plugin will have it's own dependency.
See the readmes in the subfolders for details.

# Usage
`python3 sensor_reporter configuration.ini`

An example systemd service file is provided for your reference.

1. clone this repo into `/opt/sensor_reporter`
2. create a `sensorReporter` user
3. write your config ini file
4. `sudo -u sensorReporter ln -s <path to config.ini> /opt/sensor_reporter/sensor_reporter.ini`
5. `sudo cp sensor_reporter.service /etc/systemd/system`
6. `sudo systemctl enable sensor_reporter.service`
7. `sudo sytemctl start sensor_reporter`

# Configuration
sensor_reporter uses an ini file for configuration.
The only required section is the logging section.
However, to do anything useful, there should be at least one Connection and at least one Sensor or Actuator.
All logging will be published to standard out.
In addition logging will be published to syslog or to a log file.

## Syslog Example

```ini
[Logging]
Syslog = YES
Level = INFO
```
`Syslog` can be any boolean value.
When true no other parameters are required.
`Level` is the default logging level for the core parts of sensor_reporter and any plug-in that doesn't define it's own `Level` parameter.

## Log File Example

```ini
[Logging]
File = /var/log/sensorReporter.log
MaxSize = 67108864
NumFiles = 10
Syslog = NO
Level = INFO
```
`File` is the path to the log file.
`MaxSize` is the maximum size of the log file in bytes before it gets rotated.
`NumFiles` is the number of old log files to save, older files are automatically deleted

The above parameters are only required if `SysLog` is a false value.
`Level` is the same as for `Syslog = True` and indicates the default logging level.

# Release Notes
This current version is a nearly complete rewrite of the previous version with a number of breaking changes.

## Breaking Changes

- Sending a `kill -1` now causes sensor_reporter to reload it's configuration instead of exiting
- No longer runnable on Python 2, tested with Python 3.7.
- All sensors inherit from the `core.sensor.Sensor` class and the constructor now only takes two arguments
- All actuators inherit from the `core.actuator.Actuator` class and the constructor now only takes two arguments
- `bluetooth.py` has been split into three separate sensor classes instead of just the one overly complicated one. There is now the BTLE Sensor, the Simple BT sensor, and the BT RSSI sensor to replace it and support the three modes.
- Across the board improved error logging and reporting.
- The set of required and optional parameters has changed for all sensors, actuators, and connections.
- The DHT Sensor is rewritten to use the new adafruit-blinkie library as the Adafruit_DHT library is deprecated.
- The RPi GPIO sensor no longer directly supports calling actuators or handlers. Instead the Local connection replaces this capability in a more generic way that works for all sensors. Rather than creating a handler, create an Actuator and connect a sensor to the Actuator by adding a Local connection to both.
- The LWT topic and message is now hard coded as is the refresh topic. When sensor_reporter connects it publishes ONLINE as a retained message to the LWT topic. When closing down or as a LWT OFFLINE is posted as a retained message.
- The REST communicator has been made specific to openHAB, but added the ability to work in both directions. sensor_reporter can now receive messages by commanding openHAB Items in addition to updating Items.

## Other changes
- Logs out to standard out in addition to Syslog or log files.
- Reogranized singal handleing to make it simpler.
- Moved the polling to a separate class.
- If a sensor is still running from a previous poll period, the next poll will be skipped until the sensor polling completes.
- Bluetooth LE now supports more than one device per sensor.
- The exec sensor and exec actuator now support timeouts to keep a command line from hanging forever. The exec sensor is hard coded to 10 seconds. The exec sensor has a parameter that can be set in the ini file.
- Added a Local connection which lets sensors send messages to Actuators. For example, a temperature sensor can turn on an LED light when the temperature is above a threshold.
- Improved error reporting and added a timeout to the arp sensor.
- Dash sensor has been rewritten to use the Scapy AsynchSniffer which fixes the problem where the sensor blocks sensor_repoter from exiting on a kill signal.
- Conforms to pylint PEP-8 where feasable.
- Signigficatin reduction in duplicated code and hopefully the overall structure and way it works is more straight forward.
