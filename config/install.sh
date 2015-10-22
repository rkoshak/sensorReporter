#!/bin/sh

# Assumes we are running it from the install directory

#echo "Installing paho"
#pip install paho-mqtt

#echo "Installing bluetooth"
#sudo apt-get install bluez python-bluez

#echo "Creating soft link in /opt"
#cd ..
#sudo ln -s `pwd` /opt/mqttReporter

#echo "Setting config"
#ln -s $HOSTNAME.ini /opt/mqttReporter/mqttReporter.ini

echo "Installing start script"
# Upstart
#sudo cp ./config/mqttReporter /etc/init.d
#sudo update-rc.d mqttReporter defaults

# systemd
sudo cp ./config/mqttReporter.service /etc/systemd/system
sudo systemctl enable mqttReporter.service
