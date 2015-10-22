# mqttReporter
A python script that polls a sensor and pubishes changes in its state to MQTT. It currently supports Raspberry Pi GPIO pins and Bluetooth device scanning.

# Dependencies
This script depends on the paho library, the webiopi library for GPIO, and python-bluez. The install.sh in the config folder lists all the commands necessary to install dependencies, link the current folder to /opt and set it up to start as a service. It has the scripts and commands for both upstart and systemd.

If running on a Raspberry Pi and using the GPIO sensors it must be run as root.

# Organization
The config folder contains an install.sh as descrived above, mqttReporter start script for upstart systems (raspbian wheezy), and a service file for systemd type systems (raspbian jessey, Ubuntu 15+). The install script will install dependencies using using apt-get and pip and copy and enable the start script to init.d so mqttReporter will start as a service during boot. You must edit the script to match your system.

The main folder has a default.ini with configuration parameters and the Python script itself.

The install.sh expects there to be a .ini file that matches your hostname. It will create a symbolic link to mqttReporter.ini.

If you place the script somewhere other than /opt/mqttReporter you need to update the start script with the correct path.

# Configuration
The configuration file contains 1 or more Sensor sections which specify thei Type, the MQTT topic to report to, sensor specific info (e.g. pin, BT address, etc.).

The Logging section allows one to specify where the scripts log file is saved, its max size, and maximum number of old log files to save.

The MQTT section is where one specifies the user, password, host, and port, for the MQTT Broker. The Topic item in this section is a topic the script listens to report the state of the pins on command. One also defines a Last Will and Testament topic and message so other servers can monitor whether this script is running.

# Usage
To run the script manually:

sudo python mqttReporter mqttReporter.ini

If it has been installed, run:
sudo service mqttReporter start
or
sudo systemctl start mqttReporter

# Behavior
The script will poll the sensors once per configured poll period. If the state of the sensor has changed since the last poll the state is published on the configured MQTT topic.

The GPIO sensor pins will report "OPEN" for active pins and "CLOSED" for inactive pins. The Bluetooth scanner will report "ON" when the device is present and "OFF" when it is not.

Upon receipt of any message on the incoming topic, the script will publish the current state of all configured sensors on their respective topics immediately.

The script is configured to respond properly to term signals (e.g. <ctrl>-c) so it behaves nicely when run as a service.

# Bluetooth
To discover the address of your Bluetooth device (e.g. a phone), put it in pairing mode, run inquiry.py and record the address next to the name of your device. Use this address in the .ini file for your Bluetooth scanning sensors.

inquiry.py is part of the pybluez project and can be found at https://code.google.com/p/pybluez/source/browse/examples/simple/inquiry.py
