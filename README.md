# sensorReporter
A python script that polls a sensor and pubishes changes in its state to MQTT
and/or REST. It currently supports Raspberry Pi GPIO pins,Bluetooth device
scanning, and Dash button press detection.

# Dependencies
This script depends on the paho library for MQTT, the webiopi library for GPIO,
python-bluez for Bluetooth, and scapy for Dash button support. The install.sh in 
the config folder lists all the commands necessary to install dependencies, link
the current folder to /opt and set it up to start as a service. It has the 
scripts and commands for both upstart and systemd.

If running on a Raspberry Pi and using the GPIO sensors it must be run as root.

# Organization
The config folder contains an install.sh as described above, mqttReporter start 
script for upstart systems (e.g raspbian wheezy), and a service file for systemd 
type systems (e.g raspbian jessey, Ubuntu 15+). The install script will install 
dependencies using using apt-get and pip and copy and enable the start script to 
init.d so mqttReporter will start as a service during boot. You must edit the 
script to match your system.

The main folder has a default.ini with configuration parameters and the Python 
script itself.

The install.sh expects there to be a .ini file that matches your hostname. It 
will create a symbolic link to sensorReporter.ini.

If you place or link the script somewhere other than /opt/sensorReporter you need 
to update the sensorReporter start script or sensorReporter.service with the correct 
path.

# Configuration
The configuration file contains one or more Sensor sections which specify thier 
Type, the MQTT/REST destination to report to, reporting type (MQTT or REST), sensor
specific info (e.g. pin, BT address, etc.).

The Logging section allows one to specify where the scripts log file is saved, 
its max size, and maximum number of old log files to save.

The REST section is where one specifies the biggining portion of the URL for the
REST API.

The MQTT section is where one specifies the user, password, host, and port, for 
the MQTT Broker. The Topic item in this section is a topic the script listens to 
report the state of the pins on command. One also defines a Last Will and 
Testament topic and message so other servers can monitor whether this script is 
running.

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
press.

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
