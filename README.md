NOTE: I've recently updated this to use Python3. I'm also in the middle of a complete rewrite so stay tuned.

# sensorReporter
A Python script that bridges sensors and actuators to MQTT and/or REST. 
It was written to support integrating remote sensors with openHAB, but it should support any remote hub that has a simple HTTP GET based REST API or uses MQTT.

The script currently supports MQTT and openHAB 1.x's REST API for publishing sensor readings and actuator results.
It will only work with openHAB 2.x if ClassicUI is installed.
It will not work with openHAB 3 without modifications.
It supports MQTT for receiving commands to activate actuators.

The currently supported technologies are: Raspberry PI GPIO sensors and actuators, Bluetooth presence detection sensors, Dash Button presses (deprecated), Roku IP address discovery, executing command line programs, DHT11/22 senors, a hearbeat publisher, and listening for Govee BTLE temp/humi sensors.

# Architecture
The main script is sensorReporter.py. this script parses the configuration ini file and implements the main polling loop and thread management. 
During startup this script reads the ini file and creates instances of the indicated classes and passes them the arguments for that class.

The script has been made generic and easily expanded through plugins. 
To add a new sensor or actuator simply put the new class file(s) in the same folder, fill out the ini file section and sensorReporter will handle the rest. 
The same is true for Connections.

# Dependencies
The core of the script does not have any dependencies beyond running in Python 3. 
It's been tested with Python 3.7.
However each plugin may have its own dependencies.

MQTT depends on the Paho library.
`pip3 install paho-mqtt`

The Native Raspberry Pi GPIO library comes with Raspbian by default and requires sensorReporter be run as root or by as user who is a member of the GPIO group.
If it's not installed use: 
`sudo apt-get install rpi.gpio`.

Bluetooth depends on bluez, python-bluez and bluepy (for bluetooth LE scanning).
```
sudo apt-get install bluez python-bluez
pip3 install bluepy
```

Dash requires scapy and it requires sensorReporter be run as root.
`sudo pip install scapy`

Roku does not require anything special to be installed.

Execute actuator does not require anything special to be installed.

DHT11/22 requires the Adafruit DHT library.
`sudo pip3 install Adafruit_DHT`

# Organization
The config folder contains a sensorReporter start script for upstart systems (e.g raspbian wheezy), and a service file for systemd type systems (e.g raspbian jessey+, Ubuntu 15+). 
There is an install.sh script which shows the install steps to get the dependencies using using apt-get and pip3 and to copy and enable the start script to init.d or systemd/services so sensorReporter will start as a service during boot. 
You must edit the commands in the script to match your system. 
This script is intended to be informational, not to be executed as is.

The main folder has a default.ini with configuration parameters and the Python script itself. 
The default.ini has example configurations for all of the supported addons with some comments to describe the parameter's meanings.

The services files expect there to be a sensorReporter.ini file

If you place or link the script somewhere other than /opt/sensorReporter you need to update the sensorReporter start script or sensorReporter.service with the correct path.

# Configuration
default.ini is the primary documentation for each plugin's configuration outside of the code itself. 
All the supported options and what they mean is documented in the comments.

The configuration file contains zero or more Sensor and/or Actuator sections which specify their Type, the MQTT/REST destination to report to, communciation type (MQTT or REST), and sensor/actuator specific info (e.g. pin, BT address, etc.).

The Logging section allows one to specify where the scripts log file is saved, its max size, and maximum number of old log files to save. 
When Syslog is enabled all logging goes to the system syslog instead.

The REST section is where one specifies the beggining portion of the URL for the REST API. 
For openHAB, this is the full REST URL to the Item without the Item name. 
The Item name is specified as the destination in the sensor/actuator sections.

The MQTT section is where one specifies the user, password, host, and port, for the MQTT Broker. 
The Topic item in this section is a topic the script listens to report the state of the sensors on command (i.e. any message sent to this topic will cause sensorReporter to publish the current state of all its configured sensors. 
One also defines a Last Will and Testament topic and message so other servers can monitor when sensorReporter goes offline.

Note that Actuators only support MQTT communicators.
The REST API communicator cannot receive messages, only publish.

# Usage
To run the script manually:

`sudo python3 sensorReporter sensorReporter.ini`

If it has been configured as a service, run:

`sudo service sensorReporter start`

or

`sudo systemctl start sensorReporter`

# Behavior
Some sensors spin off a separate thread to listen for updates.
These have a polling period of -1.
These include the Dash Button, Govee, and GPIO sensors.

Other sensors have a polling period.
The script will poll the sensors once per configured poll period. 
If the state of the sensor has changed since the last poll the state is published on the configured MQTT/REST destination.

The GPIO sensor pins will report "OPEN" for active pins and "CLOSED" for inactive pins.

The Bluetooth scanner will report "ON" when the device is present and "OFF" when it is not. 
Bluetooth LE scanning is tested with a Gigaset G-tag but should work with any tag. 
It checks only for presence of the device, the parameters are not used. 
If the device is found, a keyword will be reported. 
The keywords can be modified in the ini file, default values are "ON" and "OFF".

Dash will report "Pressed" when it detects the button press.

The Roku scanner will publish the detected IP address for that Roku.

The exec actuator will publish the result printed by the executed script, or ERROR if the script didn't return a 0 exitcode.

The heartbeat sensor will publish the uptime in milliseconds to destination/number and the uptime in DD:HH:MM:SS to destination/string once per polling period.

Upon receipt of any message on the main incoming destination, the script will publish the current state of all configured polling sensors (sensors with a polling period &gt; 0) on their respective destinations immediately. 
Those with a 0 polling period will not report their current status.

The script is configured to respond properly to term signals (e.g. &lt;ctrl&gt;-c) so it behaves nicely when run as a service (currently broken when using Dash).

# Bluetooth Specifics
To discover the address of your Bluetooth device (e.g. a phone), put it in pairing mode, run `inquiry.py` and record the address next to the name of your device. 
Use this address in the .ini file for your Bluetooth scanning sensors.

`inquiry.py` is part of the pybluez project and can be found at https://code.google.com/p/pybluez/source/browse/examples/simple/inquiry.py

# Dash Button Specifics (deprecated)
To discover the address of your Dash button, there is a `getMac.py` script in the config folder that will run for a short time and print the MAC address of any device that issues an ARP request while it is running. 
Run the script and then press the button and it will print that button's address. 
If you are in a noisy network with lots of ARP requests you may need to do trial and elimination to discover which MAC is for your button. 

Upon receiving your Dash button, follow the configuration steps up to the point where it asks you to choose a product. 
Close the setup app at this point and whenever you press the button the request will fail (i.e. you won't order anything) but it will be able to join your network and issue the ARP request we use to tell when it is pressed.

The code and approach to using Dash is inspired from the example found at https://medium.com/@edwardbenson/how-i-hacked-amazon-s-5-wifi-button-to-track-baby-data-794214b0bdd8#.kxt3lt5rh

Follow the default.ini example to map the MAC address to a destination. 
When sensorReporter detects the ARP packet from that button it will send the string "Pressed" to the corresponding destination. 
For example, if you have an Address1, it will send "Pressed" to Destination1.

Note that in openHAB 2 there is now a Dash binding which you should use instead.

# Roku Specifics
The "Name" of the Roku is the device's serial number. 
This can be found printed on the label on the bottom of your Roku device or found in the "My linked devices" section on your roku.com account page.

# DHT Specifics
Supported DHT sensors is DHT22, it can either run in Advanced Mode or Simple Mode. 
In Simple mode it just reads data from the sensor, and verifies that it is between bounds and returns the reading. 

In Advanced mode it reads the value and stores last five readings in an array. 
The returned value is the mean value of the readings in the array. 
This approach can be used if you encounter some readings that are wrong every now and then.
  
Be sure that Adafruits DHT Python library is installed, instructions can be found at
https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/software-install-updated

# Exec Specitics
The exec sensor will periodically execute the given shell script and publish the result or 'ERROR' if the script didn't return a 0 exitcode to the configured destination.
Avoid making the polling period shorter than it takes the script to run in the worst case or else you will run out of threads to run the sensorReporter.

# Govee Temp/Humidity Sensor
This capability has only been tested with the [H5072](https://www.govee.com/products/36/govee-bluetooth-temperature-humidity-monitor) and is based on the code at https://github.com/Thrilleratplay/GoveeWatcher.
The Govee sensor requires the bleson library to be installed as well as bluetooth.

```
sudo apt install bluetooth
sudo pip3 install bleson
```
I've only tested it running as root.
To run as another user that user will have to be added to some groups.
I don't know what those are as of this writing.

Each sensor has a unique name (e.g. GVH5072_8E33) where the last four digits are the last four digits of the devices BT MAC address.
A root for the MQTT topics is supplied as an initialization parameter and the rest of the topics take on the format:

```
<root>/<name>/temp_C  # The temperature in C
<root>/<name>/temp_F  # The temperature in F
<root>/<name>/humi    # The humidity as a percent
<root>/<name>/battery # The percentage left on the battery
<root>/<name>/rssi    # The signal strength
```

The sensor reports every two to ten seconds.

NOTE: This was tested on an RPi 3 with the built in BT and it was only able to receive a reading once every 30 minutes or so.
On an RPi 1 with a BT 4.0 dongle it receives most of the broadcasts.
YMMV.
