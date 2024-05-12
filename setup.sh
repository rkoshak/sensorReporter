#!/bin/bash

# Copyright 2023 Daniel Decker
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# INFO: This script performs the initial setup required to use sensorReporter.py. 
#		It will create the Python virtual environment, optionally create a logging director,
#		add a sensorReporter user, install the service or install desired the dependencies.		
#
# Usage: sudo ./setup.sh [--uninstall] [--yes]
#		 The script must be executed from the sensorReporter base directory, e. g. /srv/sensorReporter
#		 Flags:	--uninstall		: Removes the Python virtual environment, the logging directory, the sensorReporter user and the service
#				--yes			: The script will run without interaction, all questions are answered with yes. Useful for automation/scripting. 

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
CMD_UNINSTALL_STR='--uninstall'
CMD_YES_STR='--yes'
UNINSTALL_PY_VENV='bin lib include pyvenv.cfg'
SERVICE_WD='WorkingDirectory='
SERVICE_EXEC='ExecStart='
SERVICE_PYPATH='/bin/python'
SERVICE_FILE_PATH='/etc/systemd/system/sensor_reporter.service'
USAGE_HINT='Usage: sudo ./setup.sh [--uninstall] [--yes]'
SCRIPT_INFO="This script will install all necessary prerequisites for $APP_NAME.\nTo remove everything this script has previously installed add '--uninstall'.\nThe '--yes' flag will skip all questions and answer them with yes!"
USAGE_INSTALL_DEP="  sudo ./install_dependencies.sh [--uninstall] <plug-in folders separated by ','>"
USAGE_SENSOR_REPORTER="cd $(printf "%q" "$PWD") \nbin/python sensor_reporter.py sensor_reporter.yml"
USAGE_SEVICE='sudo systemctl enable sensor_reporter.service \nsudo systemctl start sensor_reporter.service'

# script must run as root 
if [ $ROOT_USER != "$(whoami)" ]; then
	echo "$USAGE_HINT"
	echo -e "$SCRIPT_INFO"
	exit 1
fi

# WELCOME message
echo "╔═════════════════════════════════════════════════╗"
echo "║         $APP_NAME setup script             ║"
echo "╚═════════════════════════════════════════════════╝"
echo "Present working directory: $PWD"

# check if  dependencies exist
if [ ! -e "$PWD/$DEP_SCRIPT" ]; then
	echo "Err: Required dependency '$DEP_SCRIPT' not found in present working directory!"
	echo "     Make sure your run the setup script from the $APP_NAME base folder."
	echo "$USAGE_HINT"
	exit 1
fi

# check for optional parameters in executation parameter string ($*)
if [[ $* == *"$CMD_UNINSTALL_STR"* ]]; then
	UNINSTALL=1
fi
if [[ $* == *"$CMD_YES_STR"* ]]; then
	YES_TO_ALL=1
fi
if [ "$UNINSTALL" ]; then
	echo "Script runs in uninstall mod!"
    echo "The Python virutal envionment, the logging folder, the sensorReporter user and the service will be removed."
    if [ ! "$YES_TO_ALL" ]; then
    	echo -n "Continue? (y/n): "
		read -r LINE
		if [ "$LINE" != 'y' ]; then
			exit 1
		fi
    fi
elif [ "$YES_TO_ALL" ]; then
	echo "YES MODE: service and a log folder will be created, but only base dependecies will be installed!"
	echo "Install additional dependencies via:"
	echo "$USAGE_INSTALL_DEP"
	sleep 1
fi

# only ask for user choices when installing
if [ ! "$UNINSTALL" ]; then
	# install service? 
	if [ "$YES_TO_ALL" ]; then
		INST_SERVICE=y
	else
		echo -n "Install $APP_NAME service? (y/n): "
		read -r INST_SERVICE
	fi
	
	# install logDir?
	if [ "$YES_TO_ALL" ]; then
		CREATE_LOG_DIR=y
	else
		echo -n "Create logging directory '$LOG_DIR'? (y/n): "
		read -r CREATE_LOG_DIR
	fi
	
	# don't ask for optional dependencies in --yes mode
	if [ ! "$YES_TO_ALL" ]; then
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
	fi
fi

# find default user
DEFAULT_USER=$(id -un -- $USER_ID)

if [ "$UNINSTALL" ]; then
	### uninstall mode ###
	# remove python virtual env (several folders and one cfg file)
	echo "=== removing Python virtual environment ==="
	rm -rf $UNINSTALL_PY_VENV
	
	# remove logging folder
	echo "=== removing log directory ==="
	rm -rf "$LOG_DIR"
	
	# stop and remove service if installed
	if [ -e "$SERVICE_FILE_PATH" ]; then
		echo "=== removing $APP_NAME service ==="
		systemctl stop sensor_reporter.service
		systemctl disable sensor_reporter.service
		rm "$SERVICE_FILE_PATH"
	fi
	
	# remove user
	echo "=== removing $SR_USER user ==="
	deluser "$SR_USER"
	
else
	### install mode ###
	# install basic dependencies
	echo "=== installing basic dependencies ==="
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
		echo "=== creating $SR_USER user ==="
		adduser --system --force-badname --home "$PWD" "$SR_USER"
	
		# install service
		echo "=== installing service ==="
		# if sensorReporter path is not $SETUP_FOLDER modify service file
		if [ "$PWD" != "$SETUP_FOLDER" ]; then
			# The sensorReporter service contains the working directory and the executation path,
			# moth must be modified. Systemd expects the WorkingDirectory without any character escaped (e. g. whitespace must not be escaped).
			# For ExecStart its the other way around: The path must be escaped via 'systemd-escape'
			
			# Escape sepecial charters for sed, so sed ignores '&' and other characters. sed will resolve the input
			# using '~' as sed command seperator (s~serach~replace~flag) to avoid conflicts with character used in $PWD
			PWD_SED=$(printf "%q" "$PWD")
			# search for the service working directory and update it, then write to new file 
			sed "s~$SERVICE_WD.*~$SERVICE_WD$PWD_SED~" sensor_reporter.service > sensor_reporter_edit.service
			
			# Special characters are not allowed in the service file, since sed will unescape the input we need to double escape the PWD
			# systemd-escape will replace '/' with '-' first undo this and then add escape every '\'
			PWD_EXEC=$(systemd-escape "$PWD" | sed -e 's~-~/~g' -e 's~\\~\\\\~g')
			# serach for the EXEC path and update the first part (the part until the first white space)
			sed -i "s~$SERVICE_EXEC\S*~$SERVICE_EXEC$PWD_EXEC$SERVICE_PYPATH~" sensor_reporter_edit.service
			cp sensor_reporter_edit.service "$SERVICE_FILE_PATH"
		else
			cp sensor_reporter.service "$SERVICE_FILE_PATH"
		fi
	else
	   # if service not used, we use the default_user for file and folder ownership
       SR_USER="$DEFAULT_USER"
	fi	
	
	if [ "$CREATE_LOG_DIR" ] && [ "$CREATE_LOG_DIR" = 'y' ]; then
		# create logDir
		echo "=== creating logging directory ==="
		mkdir "$LOG_DIR"
		
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
	
	# set owner and permision for sensor_reporter root folder so temp files e.g. by lgpio can be written
	chown "$SR_USER":"$DEFAULT_USER" "$PWD"
	chmod ug+rw "$PWD"
	
	# create python virtual envionment
	# allow access to system packages
	# don't run as root
	echo "=== creating Python virtual environment ==="
	su -c "python3 -m venv --system-site-packages ." "$DEFAULT_USER"
	
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
fi
