# sensorReporter
A Python script that bridges sensors and actuators to MQTT and/or REST. It was
written to support integrating remote sensors with openHAB, but it should 
support any remote device that has a simple REST API or uses MQTT.

The script currently supports MQTT and openHAB 1.x's REST API for publishing 
sensor readings and actuator results. It supports MQTT for receiving commands
to activate actuators.

The currently supported technologies are: Raspberry PI GPIO (both WebIOPi and 
Raspbian's native python library, though WebIOPi is deprecated so don't use it)
sensors and actuators, Bluetooth presence detection sensors, Dash Button 
presses, Roku IP address discovery, and executing command line programs.

# Architecture
The main script is sensorReporter.py. this script parses the configuration ini 
file and implements the main polling loop and thread management. During startup
this script reads the ini file and creates instances of the indicated classes
and passes them the arguments for that class.

The script has been made generic and easily expanded through plugins. To add a
new sensor or actuator simply put the new class file(s) in the same folder, 
fill out the ini file section and sensorReporter will handle the rest. There is
no longer a need to edit sensorReporter.py to add new capability. The same is 
true for Connections.

NOTE: I have simple RFM69 gateway addon as well but cannot publish it here due
to license conflicts, not sure if I can publish it at all, even in a separate 
repo, because GPL 3.0 forbids linking to non-GPL 3.0 code.

# Dependencies
The core of the script does not have any dependencies. However each addon may 
have its own dependencies.

MQTT depends on the Paho library.

WebIOPi GPIO sensors depend on the WebIOPi library and it requires 
sensorReporter be run as root or a user who is a member of the GPIO group.

The Native Raspberry Pi GPIO library comes with Raspbian by default.

Bluetooth depends on bluez and python-bluez

Dash requires scapy and it requires sensorReporter be run as root

Roku does not require anything special be installed

Execute actuator requires subprocess32 if executed on a Posix system with Python 
2.7

The install.sh in the config folder lists all the commands necessary to install 
dependencies, link the current folder to /opt and set it up to start as a 
service. It has the scripts and commands for both upstart and systemd.

# Organization
The config folder contains an install.sh as described above, sensorReporter start 
script for upstart systems (e.g raspbian wheezy), and a service file for systemd 
type systems (e.g raspbian jessey, Ubuntu 15+). The install script shows the 
install steps to get the dependencies using using apt-get and pip and to copy 
and enable the start script to init.d so sensorReporter will start as a service 
during boot. You must edit the script to match your system. This script is 
intended to be informational, not to be executed as is.

The main folder has a default.ini with configuration parameters and the Python 
script itself. The default.ini has example configurations for all of the 
supported addons with some comments to describe the parameter's meanings.

The install.sh expects there to be a .ini file that matches your hostname. It 
will create a symbolic link to sensorReporter.ini.

If you place or link the script somewhere other than /opt/sensorReporter you need 
to update the sensorReporter start script or sensorReporter.service with the correct 
path.

# Configuration
The configuration file contains one or more Sensor and/or Actuator sections 
which specify thier Type, the MQTT/REST destination to report to, communciation 
type (MQTT or REST), and sensor/actuator specific info (e.g. pin, BT address, 
etc.).

The Logging section allows one to specify where the scripts log file is saved, 
its max size, and maximum number of old log files to save. When Syslog is 
enabled all logging goes to the system syslog.

The REST section is where one specifies the biggining portion of the URL for the
REST API. For openHAB, this is the full REST URL to the Item without the Item
name. The Item name is specified as the destination in the sensor/actuator 
sections.

The MQTT section is where one specifies the user, password, host, and port, for 
the MQTT Broker. The Topic item in this section is a topic the script listens to 
report the state of the sensors on command (i.e. any message sent to this topic 
will cause sensorReporter to publish the current state of all its configured 
sensors. One also defines a Last Will and Testament topic and message so other 
servers can monitor when sensorReporter goes offline.

# Usage
To run the script manually:

sudo python sensorReporter sensorReporter.ini

If it has been installed, run:

sudo service sensorReporter start

or

sudo systemctl start sensorReporter

# Behavior
The script will poll the sensors once per configured poll period. If the state 
of the sensor has changed since the last poll the state is published on the 
configured MQTT/REST destination.

The GPIO sensor pins will report "OPEN" for active pins and "CLOSED" for 
inactive pins. The Bluetooth scanner will report "ON" when the device is present 
and "OFF" when it is not. Dash will report "Pressed" when it detects the button
press. The Roku scanner will publish the detected IP address for that Roku.
The exec actuator will publish the result printed by the executed script, or
ERROR if the script didn't return a 0 exitcode.

Upon receipt of any message on the incoming destination, the script will publish the 
current state of all configured polling sensors (sensors with a polling period 
&gt; 0) on their respective destinations immediately.

The script is configured to respond properly to term signals (e.g. &lt;ctrl&gt;-c) so 
it behaves nicely when run as a service (currently broken when using Dash).

# Bluetooth Specifics
To discover the address of your Bluetooth device (e.g. a phone), put it in 
pairing mode, run inquiry.py and record the address next to the name of your 
device. Use this address in the .ini file for your Bluetooth scanning sensors.

inquiry.py is part of the pybluez project and can be found at 
https://code.google.com/p/pybluez/source/browse/examples/simple/inquiry.py

# Dash Button Specifics
To discover the address of your Dash button, there is a getMac.py script in the
config folder that will run for a short time and print the MAC address of any
device that issues an ARP request while it is running. Run the script and then
press the button and it will print that button's address. If you are in a noisy
network with lots of ARP requests you may need to do trial and elimination to
discover which MAC is for your button. Both of my buttons start with 74 but I
don't know if that is a pattern that holds across all buttons.

Upon receiving your Dash button, follow the configuration steps up to the point
where it asks you to choose a product. Close the setup app at this point and 
whenever you press the button the request will fail (i.e. you won't order 
anything) but it will be able to join your network and issue the ARP request we
use to tell when it is pressed.

The code and approach to using Dash is inspired from the example found at
https://medium.com/@edwardbenson/how-i-hacked-amazon-s-5-wifi-button-to-track-baby-data-794214b0bdd8#.kxt3lt5rh

Follow the default.ini example to map the MAC address to a destination. When 
sensorReporter detects the ARP packet from that button it will send the string
"Pressed" to the corresponding destination. For example, if you have an Address1,
it will send "Pressed" to Destination1.

# Roku Specifics
The "Name" of the Roku is the device's serial number. This can be found printed 
on the label on the bottom of your Roku device or found in the "My linked 
devices" section on your roku.com account page.
