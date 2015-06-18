# mqttReporter
A python script that runs on a Raspberry Pi to report the state changes of GPIO pins to MQTT topics. It depends on webiopi for interaction with the GPIO pins and paho for MQTT.

# Dependencies
This script depends on the webiopi and paho libraries. The install.sh will pip install paho for you but installing webiopi is an exercise left to the student.

Because the script accesses the GPIO pins, it must be run as root.

# Organization
The config folder contains an install.sh and a mqttReporter start script. The install script will install paho using pip and copy and enable the start script to init.d so mqttReporter will start as a service during boot.

The main folder has a default.ini with configuration parameters and the script itself.

If you create a new name for default.ini, make sure to update config/mqttReporter so it calls the script with the correct configuration file. Also, if you place the script somewhere other than /opt/mqttReporter you need to update the start script with the correct path.

# Configuration
The configuration file contains 1 or more Sensor sections which specify the pin, the MQTT topic to report to, and whether the sensor on the pin is Pull Up or Pull Down so it can handle normally open and normally closed sensors.

The Logging section allows one to specify where the scripts log file is saved, its max size, and maximum number of old log files to save.

The MQTT section is where one specifies the user, password, host, and port, for the MQTT Broker. The Topic item in this section is a topic the script listens to report the state of the pins on command.

# Usage
To run the script manually:

sudo python mqttReporter default.ini

If it has been installed, run:
sudo service mqttReporter start

# Behavior
The script will check the state of the pins every second. If the state of the pin changed since the last time it was checked the new state is published to the MQTT topic. If the state of the pin is LOW the string "CLOSED" is published. If HIGH, "OPEN" is published.

Upon receipt of any message on the incoming topic, the script will publish the current state of all configured pins on their respective topics immediately.

The script is configured to respond properly to term signals (e.g. <ctrl>-c) so it behaves nicely when run as a service.
