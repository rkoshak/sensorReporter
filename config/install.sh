#!/bin/sh

#echo "Installing paho"
pip install paho-mqtt

echo "Installing start script"
cp mqttReporter /etc/init.d

echo "Setting start script to run at boot"
update-rc.d mqttReporter defaults

