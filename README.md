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

| Plug-in                                                                                                   | Type                          | Purpose                                                                                                   |
|---------------------------------------------------------------------------------------------------------- |-------------------------------|---------------------------------------------------------------------------------------------------------- |
| [`bt.btle_sensor.BtleSensor`](bt/README.md#btbtle_sensorbtlesensor)                                       | Background Sensor             | Scans for BTLE advertisements from configured devices.                                                    |
| [`bt.btscan_sensor.SimpleBtSensor`](bt/README.md#btbtscan_sensorsimplebtsensor)                           | Polling Sensor                | Scans for the presence of BT devices with a given addresses.                                              |
| [`bt.govee_sensor.GoveeSensor`](bt/README.md#btgovee_sensorgoveesensor)                                   | Background Sensor             | Receives BTLE packets from Govee H5075 temperature and humidity sensors.                                  |
| [`energymeter.read_meter_values.Pafal20ec3gr`](energymeter/README.md#pafal_readerpafal_readerpafalreader) | Polling Sensor                | Periodically reads out an energymeter using serial device. Currently only Pafal 20ec3gr supported.        |
| [`exec.exec_actuator.ExecActuator`](exec/README.md#execexec_actuatorexecactuator)                         | Actuator                      | On command, executes the configured command line command.                                                 |
| [`exec.exec_sensor.ExecSensor`](exec/README.md#execexec_sensorexecsensor)                                 | Polling Sensor                | Executes the configured command line and publishes the result.                                            |
| [`gpio.dht_sensor.DhtSensor`](gpio/README.md#gpiodht_sensordhtsensor)                                     | Polling Sensor                | Publishes temperature and humidity readings from DHT11, DHT22, and AM2302 sensors connected to GPIO pins. |
| [`gpio.ds18x20_sensor.Ds18x20Sensor`](gpio/README.md#gpiods18x20_sensords18x20sensor)                     | Polling Sensor                | Publishes temperature reading from DS18S20 and DS18B20 1-Wire bus sensors connected to GPIO pins.         |
| [`gpio.rpi_gpio.RpiGpioSensor`](gpio/README.md#gpiorpi_gpiorpigpiosensor)                                 | Polling or Background Sensor  | Publsihes ON/OFF messages based on the state of a GPIO pin.                                               |
| [`gpio.rpi_gpio.RpiGpioActuator`](gpio/README.md#gpiorpi_gpiorpigpioactuator)                             | Actuator                      | Sets a GPIO pin to a given state on command.                                                              |
| [`gpio.gpio_led.GpioColorLED`](gpio/README.md#gpiogpio_ledgpiocolorled)                                   | Actuator                      | Commands 3 to 4 GPIO pins to control a RGB or RGBW LED                                                    |
| [`heartbeat.heartbeat.Heartbeat`](heartbeat/README.md#heartbeatheartbeatheartbeat)                        | Polling Sensor                | Publishes the amount of time sensor_reporter has been up as number of msec and as DD:HH:MM:SS.            |
| [`local.local_conn.LocalConnection`](local/README.md#local-connection)                                    | Connection                    | Allows sensors to call actuators.                                                                         |
| [`local.local_logic.LogicOr`](local/README.md#locallocal_logiclogicor)                                    | Actuator                      | Forwards commands from multiple inputs locally to an actuator.                                            |
| [`mqtt.mqtt_conn.MqttConnection`](mqtt/README.md#mqtt-connection)                                         | Connection                    | Allows Actuators to subscribe and publish and Sensors to publish results to a MQTT server.                |
| [`mqtt.homie_conn.HomieConnection`](mqtt/README.md#homie-connection)                                      | Connection                    | Subscribe and publish sensors and actuators to a MQTT server via Homie convention.                        |
| [`network.arp_sensor.ArpSensor`](network/README.md#networkarp_sensorarpsensor)                            | Polling Sensor                | Periodically gets and parses the ARP table for given mac addresses.                                       |
| [`network.dash_sensor.DashSensor`](network/README.md#networkdash_sensordashsensor)                        | Background Sensor             | Watches for Amazon Dash Button ARP packets.                                                               |
| [`openhab_rest.rest_conn.OpenhabREST`](openhab_rest/README.md#openhab-rest-connection)                    | Connection                    | Subscribes and publishes to openHAB's REST API. Subscription is through openHAB's SSE feed.               |
| [`roku.roku_addr.RokuAddressSensor`](roku/README.md#roku-address-sensor-deprecated)                       | Polling Sensor                | Periodically requests the addresses of all the Rokus on the subnet.                                       |
| [`ic2.relay.EightRelayHAT`](i2c/README.md#i2crelayeightrelayhat)                                          | Actuator                      | Sets a relay to a given state on command. Supports 8-Relays-HAT via i2c                                   |
| [`ic2.triac.TriacDimmer`](i2c/README.md#i2ctriactriacdimmer)                                              | Actuator                      | Sets a triac PWM to a given duty cycle on command. Supports 2-Ch Triac HAT via i2c                        |
| [`i2c.pwm.PwmHatColorLED`](i2c/README.md#i2cpwmpwmhatcolorled)											| Actuator						| Commands 3 to 4 Channels on a PWM HAT to control a RGB or RGBW LED										|  

# Architecture
The main script is `sensor_reporter.py` which parses a configuration YAML file and handles operating system signal handling.

It uses a `core.poll_mgr.PollMgr` manages running a polling loop used by Polling Sensors to control querying the devices.

All connections inherit from `core.connection.Connection`.
All Actuators inherit from `core.actuator.Actuator` and all sensors inherit from `core.sensor.Sensor`.
Common code is implemented in the parent classes.

On startup or when receiving a `HUP` (`kill -1`) operating system signal the configuratuion YAML file is loaded.
There is a logging section (see below) where the logging level and where to log to is defined.
Then there is a separate section for each connection, sensor, and actuator.
Each individual plug-in will define it's own set of required and optional parameters.
See the README files in the subfolders for details.

However, some parmeters will be common.
- All polling sensors require a Poll parameter indicating how often in seconds to poll the sensor devices
- All sections require a Class parameter defining the class to load.
- All sensors and actuators require a Connections class containing a dictionary with the connections and topics to publish/subscribe through. The layout is described at the connections readme.
- All actuators require a command source, which has to be unique for the configured connection. E. g. if the same command source is used by several actuators only the last one will work. The parameter name of the command source varies differently for each connection.
- All sections have an optional Level parameter where the logging level for that plugin or sensor_reporter overall can be set. Supported levels are DEBUG, INFO, WARNING, and ERROR.

# Dependencies
sensor_reporter only runs in Python 3 and has only been tested in Python 3.7 through Python 3.11.2.
It uses PyYAML for parsing the configuration file.

## Setup
After cloning this repo to a folder (e.g. `/srv/sensorReporter`) run the following commands:

```bash
cd /srv/sensorReporter
sudo ./setup.sh
```
This will install the base dependencies and setup a virtualenv for the Python packages.
Each plugin will have it's own dependency.
See the readmes in the subfolders for details.

## Optional plug-in dependencies
Plug-in dependencies can be installed on demand using the install_dependencies.sh from the base folder:

```bash
cd /srv/sensorReporter
sudo ./install_dependencies.sh <plug-in folders separated by ','>
```
Run command without parameters to list available plug-ins.
For examples see plug-in readme's.

# Usage

1. Download sensor_reporter and execute setup.sh see section [setup](#setup)
2. Write your config file and save it to `/srv/sensorReporter/sensor_reporter.yml`. For details see section [configuration](#configuration) and the plug-in readme's
3. Start sensor_reporter manually to test the configuration with:

```bash
cd /srv/sensorReporter
bin/python sensor_reporter.py sensor_reporter.yml
```
(optional) enable & start the service:

4. set service to auto start:  `sudo systemctl enable sensor_reporter.service`
5. start sensor_reporter:  `sudo sytemctl start sensor_reporter.service`

To reload a modified sensor_reporter.yml use the command:  `sudo sytemctl reload sensor_reporter.service`  
After large changes to the configuration, e. g. sensors/actuators has been removed/added, a restart of the service is recommended.

# Configuration
sensor_reporter uses an YAML file for configuration.
The only required section is the logging section.
However, to do anything useful, there should be at least one Connection and at least one Sensor or Actuator.
All logging will be published to standard out.
In addition logging will be published to syslog or to a log file.

*Security advice:* make sure your sensor_reporter.yml is owned by the user `sensorReporter` and only that user has read and write permissions.
This user is automatically created when choosing 'install service' in setup.sh.

`sudo chown sensorReporter:nogroup sensor_reporter.yml`  
`sudo chmod 600 sensor_reporter.yml`

## Syslog Example

```yaml
Logging:
    Syslog: yes
    Level: INFO
```
`Syslog` can be any boolean value, including yes / no.
When true no other parameters are required.
`Level` is the default logging level for the core parts of sensor_reporter and any plug-in that doesn't define it's own `Level` parameter. Allowed values: `DEBUG, INFO, WARNING, ERROR`

## Log File Example

```yaml
Logging:
    File: /var/log/sensor_reporter/sensorReporter.log
    MaxSize: 67108864
    NumFiles: 10
    Syslog: no
    Level: INFO
```
`File` is the path to the log file.
`MaxSize` is the maximum size of the log file in bytes before it gets rotated.
`NumFiles` is the number of old log files to save, older files are automatically deleted

The above parameters are only required if `SysLog` is disabled.
`Level` is the same as for `Syslog: yes` and indicates the default logging level.

Make sure the user `sensorReporter` has write access:
1. `sudo mkdir /var/log/sensor_reporter`
2. `sudo chown sensorReporter:nogroup /var/log/sensor_reporter`

## Sections for Components

Note that sensor_reporter requires the section names to start with the type of the plugin.
Possible values are:
* Connection
* Actuator
* Sensor

A sensor section could thus be named `Sensor_Heartbeat` or `Actuator1`.
Section names have to be unique.

## Default section

Optionally a `DEFAULT` section can be added to the configuration.
Parameters within this section will be the default for all sensors and actuator.
Sensors and actuators can override the default if they specifie the same parameter.
This is useful when many sensors of the same type with similar parameters are used.
E. g. set the default for `TempUnit` so the DhtSensors don't need to specifie it repetitive:

```yaml
DEFAULT:
    TempUnit: F
```

# Release Notes
This current version is a nearly complete rewrite of the previous version with a number of breaking changes.

## Breaking Changes

- The configuration file is now in YAML syntax insted of a ini file - October 2022
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
