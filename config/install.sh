#!/bin/sh

# Assumes we are running it from the install directory

#echo "Installing paho"
#pip install paho-mqtt

#echo "Installing bluetooth"
#sudo apt-get install bluez python-bluez
#echo "Installing bluepy for BTLE scanning"
#pip install bluepy

#echo "Installing scapy"
#pip install scapy

#echo "Installing subprocess32" for exec capability
#pip install subprocess32

#echo "Creating soft link in /opt"
#cd ..
#sudo ln -s `pwd` /opt/sensorReporter
#chmod a+x /opt/sensorReporter/sensorReporter.py

#echo "Setting config"
#ln -s $HOSTNAME.ini /opt/sensorReporter/sensorReporter.ini

echo "Installing start script"
# Upstart
#sudo cp ./config/sensorReporter /etc/init.d
#sudo update-rc.d sensorReporter defaults

# systemd
sudo cp ./config/sensorReporter.service /etc/systemd/system
sudo systemctl enable sensorReporter.service
