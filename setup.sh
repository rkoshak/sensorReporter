#!/bin/bash

# init vars
SETUP_FOLDER='/srv/sensorReporter'
SR_USER='sensorReporter'
APP_NAME='sensorReporter'
DEP_SCRIPT='install_dependencies.sh'
DEP_FILE='dependencies.txt'
ROOT_USER='root'
USER_ID=1000
LOG_DIR='/var/log/sensor_reporter'
LOG_FILE="$LOG_DIR/sensorReporter.log"
USAGE_HINT='Usage: sudo ./setup.sh'
SCRIPT_INFO="This script will install all necessary prerequisites for $APP_NAME"
USAGE_INSTALL_DEP="  sudo ./install_dependencies.sh [--uninstall] <plug-in folders separated by ','>"
USAGE_SENSOR_REPORTER="cd $PWD \nbin/python sensor_reporter.py sensor_reporter.yml"
USAGE_SEVICE='sudo systemctl enable sensor_reporter.service \nsudo systemctl start sensor_reporter.service'

# script must run as root 
if [ $ROOT_USER != "$(whoami)" ]; then
	echo "$USAGE_HINT"
	echo "$SCRIPT_INFO"
	exit 1
fi

# WELCOME message
echo "╔═════════════════════════════════════════════════╗"
echo "║         $APP_NAME setup script             ║"
echo "╚═════════════════════════════════════════════════╝"
echo "Present working directory: $PWD"

if [ "$PWD" = "$SETUP_FOLDER" ]; then
	# install service? Only possilbe when in SETUP_FOLDER
	echo -n "Install $APP_NAME service? (y/n): "
	read -r INST_SERVICE
else
	# if setup runs from a different folder
	echo "Warn: Setup expects working directory '$SETUP_FOLDER', $APP_NAME service cannot be installed for this path."
fi
# install logDir?
echo -n "Create logging directory '$LOG_DIR'? (y/n): "
read -r CREATE_LOG_DIR

# print empty line
echo ""
# install plug-in dependencies?
echo "Which dependencies should be installed? Dependencies can be installed on demand with:"
echo "$USAGE_INSTALL_DEP"
echo "Available plug-in folders:"
# find DEP_FILE in subfolders, print only folder name, remove leading './'
find . -mindepth 2 -name "$DEP_FILE" -printf %h\\n | sed 's#./##'
echo "Write them as comma separated list, e.g. bt,gpio"
echo -n "Leave empty to skip: "
read -r PATH_LIST

# find default user
DEFAULT_USER=$(id -un -- $USER_ID)

# install basic dependencies
echo "=== running installation script ==="
if [ -x "$PWD/$DEP_SCRIPT" ]; then
	# run install_dependencies.sh with argument '.' 
	# this will install dependencies.txt from sensorReporter base directory 
	if ! "$PWD/$DEP_SCRIPT" .; then
		# if script exited with error
		echo "Err: $PWD/$DEP_SCRIPT exited with error, aborting!"
		exit 1
	fi
else
	# if dependency script not found or not executable, terminate
	echo "Err: $PWD/$DEP_SCRIPT not found or not executable!"
	exit 1
fi

if [ "$INST_SERVICE" ] && [ "$INST_SERVICE" = 'y' ]; then
	# create USER
	echo "=== creating user $SR_USER ==="
	adduser --system --force-badname --home "$SETUP_FOLDER" "$SR_USER"

	# install service
	echo "=== installing service ==="
	cp sensor_reporter.service /etc/systemd/system
fi	

if [ "$CREATE_LOG_DIR" ] && [ "$CREATE_LOG_DIR" = 'y' ]; then
	# create logDir
	echo "=== creating logging directory ==="
	mkdir "$LOG_DIR"
	
	if [ "$INST_SERVICE" ] && [ "$INST_SERVICE" != 'y' ]; then
		# if service not used, we create the LOG_DIR for the default user
		SR_USER="$DEFAULT_USER"
	fi
	# change owner and add write permission for groupe
	chown "$SR_USER":"$DEFAULT_USER" "$LOG_DIR"
	chmod g+w "$LOG_DIR"
	
	# Create empty logfile with permissions for user pi and sensorReporter 
	# to avoid permission problems when sensorReporter is started manually for the first time
	touch "$LOG_FILE"
	# change owner and add write permission for groupe
	chown "$SR_USER":"$DEFAULT_USER" "$LOG_FILE"
	chmod g+w "$LOG_FILE"
fi

# create python virtual envionment
# allow access to system packages
# don't run as root
echo "=== creating python virtual environment ==="
su -c "python -m venv --system-site-packages ." "$DEFAULT_USER"

# install plug-in dependencies
if [ "$PATH_LIST" ]; then
	echo "=== installing optional dependencies ==="
	"$PWD/$DEP_SCRIPT" "$PATH_LIST"
fi

echo ""
echo "Setup done! Now create a configuration yml-file and start sensorReporter with:"
echo -e "$USAGE_SENSOR_REPORTER"
if [ "$INST_SERVICE" ] && [ "$INST_SERVICE" = 'y' ]; then
	echo ""
	echo "To use the service, enter:"
	echo -e "$USAGE_SEVICE"
fi
