# sensorReporter
A python script that polls a sensor and pubishes changes in its state to MQTT
and/or REST as well as reacting to commands sent to it (MQTT RPi.GPIO support 
only for now). It currently supports Raspberry Pi GPIO pins through WebIOPi or
RPi.GPIO, Bluetooth device scanning, and Dash button press detection.

# Dependencies
This script depends on the paho library for MQTT, the webiopi library or the 
RPi.GPIO for GPIO, python-bluez for Bluetooth, and scapy for Dash button 
support. The install.sh in the config folder lists all the commands necessary 
to install dependencies, link the current folder to /opt and set it up to start 
as a service. It has the scripts and commands for both upstart and systemd.

If running on a Raspberry Pi and using the GPIO sensors it must be run as root
or running as a user who is a member of the gpio group if your image has 
/dev/gpiomem with appropriate permissions.

# Organization
The config folder contains an install.sh as described above, sensorReporter start 
script for upstart systems (e.g raspbian wheezy), and a service file for systemd 
type systems (e.g raspbian jessey, Ubuntu 15+). The install script will install 
dependencies using using apt-get and pip and copy and enable the start script to 
init.d or /systemd/system and enalbe it so sensorReporter will start as a service 
during boot. You must edit the script to match your system.

The main folder has a default.ini with configuration parameters, examples and the 
Python script itself.

The install.sh expects there to be a .ini file that matches your hostname. It 
will create a symbolic link to sensorReporter.ini which the service start 
scripts expect.

If you place or link the script somewhere other than /opt/sensorReporter you need 
to update the sensorReporter start script or sensorReporter.service with the correct 
path.

# Configuration
The configuration file contains one or more Sensor and/or Actuator sections which specify thier 
Type, the connection to report or subscribe to, path on the connection to report
to (e.g. MQTT Topic or REST URL), sensor and actuator specific info (e.g. pin, 
BT address, etc.).

The Connection sections contain the parameters for the connections sensorReporter
communicates through. Currently there are two supported connections, REST and 
MQTT.

The REST section is where one specifies the biggining portion of the URL for the
REST API.

The MQTT section is where one specifies the user, password, host, and port, for 
the MQTT Broker. The Topic item in this section is a topic the script listens to 
report the state of the pins on command. One also defines a Last Will and 
Testament topic and message so other servers can monitor whether this script is 
running. Finally there is an option for turning on TLS in the connection to the
MQTT Broker. It will look for the certificates in ./certs/ca.cert.

The Logging section allows one to specify where the scripts log file is saved, 
its max size, and maximum number of old log files to save.


# Usage
To run the script manually:

sudo python sensorReporter sensorReporter.ini

If it has been installed, run:

sudo service sensorReporter start

or

sudo systemctl start sensorReporter

# Behavior
There are three types of behaviors.

1. Certain sensors require polling. The Bluetooth, WebIOPi GPIO, and Raspberry Pi GPIO sensors will
poll for the current state one per configured poll period. If the state of the 
sensor has changed the new state is published to the configured MQTT/REST 
destination.

2. Other sensors are event driven and do not require polling. The Dash sensor 
is and example. These sensors will receive events and report them instead of
requiring polling. To turn off polling in the config file a Poll = -1 is used.

3. Finally, Actuators subscribe to some communication desintaion (MQTT is 
currently only supported) and perform some action when commanded. The 
rpiGPIOActuator is an example of an Actuator that will toggle or set the 
configured pin upon receipt of a message.

Upon receipt of any message on the incoming destination configured in the MQTT 
section, the script will publish the current state of all configured polling 
sensors (sensors with a polling period &gt; 0) on their respective destinations 
immediately.

The script is configured to respond properly to term signals (e.g. &lt;ctrl&gt;-c) so 
it behaves nicely when run as a service (currently broken when using Dash).

# Bluetooth Specifics
To discover the address of your Bluetooth device (e.g. a phone), put it in 
pairing mode, run inquiry.py and record the address next to the name of your 
device. Use this address in the .ini file for your Bluetooth scanning sensors.

inquiry.py is part of the pybluez project and can be found at 
https://code.google.com/p/pybluez/source/browse/examples/simple/inquiry.py

When a configured device is detected it will report "ON" to the destination. 
"OFF" is reported when the device is no longer detected.

# Dash Button Specifics
To discover the address of your Dash button, there is a getMac.py script in the
config folder that will run for a short time and print the MAC address of any
device that issues an ARP request while it is running. Run the script and then
press the button and it will print that button's address.

Upon receiving your Dash button, follow the configuration steps up to the point
where it asks you to choose a product. Close the setup app at this point and 
whenever you press the button the request will fail (i.e. you won't order 
anything) but it will be able to join your network and issue the ARP request we
use to tell when it is pressed.

The code and approach to using Dash is inspired from the example found at
https://medium.com/@edwardbenson/how-i-hacked-amazon-s-5-wifi-button-to-track-baby-data-794214b0bdd8#.kxt3lt5rh

When a Dash button press is detected "Pressed" is sent to the destination.

# WebIOPi GPIO Specifics
The pin number is the BMC number for the pin, not the board number. If the 
current state of the pin is LOW "CLOSED" is sent to the destination. If it is
HIGH "OPEN" is sent to the destination.

# RPi.GPIO Sensor Specifics
The pin number is the BMC number for the pin, not the board number. If the 
current state of the pin is LOW "CLOSED" is sent to the destination. If it is
HIGH "OPEN" is sent to the desitnation.

NOTE: Work is in progress to convert this script to no longer require polling.

# RPi.GPIO Actuator Specifics
The pin number is the BMX number for the pin, not the board number. The script 
initialzes the pin to HIGH (appears to avoid the pin being set when the script 
starts up. Upon receipt of a message, if Toggle is set to True the pin is set 
to HIGH and half a second later set to LOW. If Toggle = False the pin is set to
LOW if the received message is "ON" and HIGH otherwise.

NOTE: Work is in progress to make the HIGH/LOW behavior more flexible to 
support a wider range of applications.

WebIOPi support is deprectated and will be removed in the near future.
