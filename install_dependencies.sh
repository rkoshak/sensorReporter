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


# INFO: This script will install/remove apt and pip dependencies listed in a given $DEP_FILE (dependencies.txt).
#		To work properly, it requires root privileges (apt/adduser/deluser commands)
#		and must be run from the sensor reporter base directory.
#
# Usage: sudo ./install_dependencies.sh [--uninstall] <folders,list,separated,by,,>
#		 The expected parameter is a comma separated list of the folders within sensorReporter 
#	     that contain $DEP_FILE (dependencies.txt). 
#		 To read the $DEP_FILE inside the sensorReporter base directory, pass '.' as parameter.
# 		 The '--uninstall' parameter is optional to remove the dependencies listed in $DEP_FILE
#
#	E.g. cd /srv/sensorReporter
#		 sudo ./install_dependencies.sh gpio,bt
#		 The above command will install dependencies for 'gpio' and 'bt'
#
# Syntax for $DEP_FILE (dependencies.txt)
# 		Section name, one of [apt], [pip], [groups]
#				[apt]		install/remove specified dep-packages via 'apt'
#				[pip]		install/uninstall specified python-packages via 'pip' in the Python virtual envionment
#				[groups]	add/remove specified groups to/from $SR_USER
# 		Name of the package/group. pip packages can have version annotations e.g. paho-mqtt>=1.6.1,<2.0.0
#		Comments can be added with a '#' at the beginning of the line.
#
#	E.g.
#		[apt]
#		# required by DhtSensor
#		libgpiod2
#		[groups]
#		gpio
#		[pip]
# 		# required by DhtSensor, RpiGpioSensor, RpiGpioActuator, GpioColorLED
#		RPI.GPIO
#		# required by DhtSensor
#		adafruit-blinka
#		adafruit-circuitpython-dht
#
# Sources:
# https://askubuntu.com/questions/252734/apt-get-mass-install-packages-from-a-file
# https://stackoverflow.com/questions/49399984/parsing-ini-file-in-bash
# https://stackoverflow.com/questions/2866117/windows-batch-script-to-read-an-ini-file
# https://www.baeldung.com/linux/shell-script-iterate-over-string-list
# https://stackoverflow.com/questions/13122441/how-do-i-read-a-variable-on-a-while-loop
# https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#Here-Strings

# init vars
DEP_FILE='dependencies.txt'
SR_USER='sensorReporter'
USER_ID=1000
ROOT_USER='root'
USAGE_HINT="Usage: sudo ./install_dependencies.sh [--uninstall] <plug-in folders separated by ','>"
SCRIPT_INFO="This script will install/remove apt and pip dependencies listed in a given '$DEP_FILE'."
UNINSTALL_STR='--uninstall'

# Function install_dep() will install/remove apt, pip dependencies and add/remove groups to the SR_USER
# Parameters:
#	KIND		the kind of the dependency, currently supported:
#				[apt]			install/remove specified dep-packages via 'apt'
#				[pip]			install/uninstall specified python-packages via 'pip' in the virtual Python envionment
#				[groups]		add/remove given specified to/from $SR_USER
#				[raspi-config]  enables/disables specified raspi-config switches, see: https://www.raspberrypi.com/documentation/computers/configuration.html#raspi-config-cli
#	DEP			the name of the package/group
function install_dep()
{
	KIND=$1
	DEP=$2

	if [ "$KIND" = '[apt]' ]; then
		if [ "$LIST_UNINSTALL_DEP" ]; then
			echo debian-package: "$DEP"
		elif [ "$UNINSTALL" ]; then
			echo "=== removing $DEP ==="
			apt remove -y "$DEP"
		else
			echo "=== installing $DEP ==="
			apt install -y "$DEP"
		fi
	elif [ "$KIND" = '[groups]' ]; then
		if [ "$LIST_UNINSTALL_DEP" ]; then
			echo "user '$SR_USER' will be removed from group '$DEP'"
		elif [ "$UNINSTALL" ]; then
			echo "=== removing user '$SR_USER' from groupe '$DEP' ==="
			deluser "$SR_USER" "$DEP"
		else
			echo "=== adding user '$SR_USER' to groupe '$DEP' ==="
			adduser "$SR_USER" "$DEP"
		fi
	elif [ "$KIND" = '[pip]' ]; then
		if [ "$LIST_UNINSTALL_DEP" ]; then
			echo pip-package: "$DEP"
		elif [ "$UNINSTALL" ]; then
			echo "=== removing $DEP ==="
			# don't run as root
			# Escaped quotes will get resolved from su,
			# these quotes around $DEP will allow pip dependencies with version e.g. paho-mqtt<2.0.0,>=1.6.1
			su -c "bin/python -m pip uninstall -y \"$DEP\"" "$USER"
		else
			echo "=== installing $DEP ==="
			# don't run as root
			su -c "bin/python -m pip install \"$DEP\"" "$USER"
		fi
	elif [ "$KIND" = '[raspi-config]' ]; then
		if [ "$LIST_UNINSTALL_DEP" ]; then
			echo raspi-config switch: "$DEP"
		elif [ "$UNINSTALL" ]; then
			echo "=== disabling raspi-config switch $DEP ==="
			raspi-config nonint "$DEP" 1
		else
			echo "=== enabling raspi-config switch $DEP ==="
			# yes setting the switch to 0 will enable the feature
			raspi-config nonint "$DEP" 0
		fi
	fi
}

# Function parse_dep() reads a given dependencies.txt and parses it
# Parameters:
#	DEP_PATH		the full path to a dependencies.txt incliding the file itself
function parse_dep()
{
	DEP_PATH=$1
	# parse $DEP_PATH,
	#	remember lines starting with '[' as prefix 
	#	ignore lines starting with #
	DEPENDENCIES=$(awk  '/\[/{prefix=$0; next}
						/\#/{next}
						$1{print prefix " " $0":"}' "$DEP_PATH")

	IFS="$OLD_IFS"
	# Call install function for every dependency
	# Use custom internal field separator ":" to separate DEPENDENCIES
	# while using default IFS to process each entry.
	# Following characters are note aviable as IFS cos they are used by pip: >=<,.
	while IFS=":" read -r kind_dep; do
		# variable '$kind_dep' contains one space ' '
		# the default IFS will separate it in two arguements ($kind and $dep)
		install_dep $kind_dep
	done <<<"$DEPENDENCIES"
}

# Function print_usage() prints cli usage info and aviable plug-in folders
function print_usage()
{
	echo "$USAGE_HINT"
	echo "$SCRIPT_INFO"
	echo -e "\nAvailable plug-in folders:"
	# find DEP_FILE in subfolders, print only folder name, remove leading './'
	find . -mindepth 2 -name "$DEP_FILE" -printf %h\\n | sed 's#./##'
}

### start main script ###

# if no parameters given or user is not root, print usage & exit 
if [ "$#" -eq 0 ] || [ "$ROOT_USER" != "$(whoami)" ]; then
	print_usage
	exit 1
fi

# check dependecies
if [ ! -e "$PWD/$DEP_FILE" ]; then
	echo "Err: Required dependency '$DEP_FILE' not found in present working directory ($PWD)!"
	echo "     Make sure your run the install_dependencies script from the sensorRepoter base folder."
	echo "$USAGE_HINT"
	exit 1	
fi

# if uninstall flag is set activate LIST_UNINSTALL_DEP mode
if [ "$1" = "$UNINSTALL_STR" ]; then
	if [ "$#" -lt 2 ]; then
		# if less then 2 arguments are used print usage and exit
		print_usage
		exit 1
	fi
	LIST_UNINSTALL_DEP=1
	# save specified folder list
	PATH_LIST=$2
	echo "Script runs in uninstall mode!"
	echo "The following packages will be removed regardless of their dependencies on other software:"
else
	# save specified folder list
	PATH_LIST=$1
	INSTALL=1
	
	# update repositories
	apt update
fi

# get username of default user
USER=$(id -un -- $USER_ID)

# check if sensorRepoter user exists
if [ "$(id $SR_USER >/dev/null 2>&1)" ]; then
	# if not use default user instead
	SR_USER="$USER"
fi

# repeat while LIST_UNINSTALL_DEP or UNINSTALL or INSTALL are not empty
while [ "$INSTALL" ] || [ "$LIST_UNINSTALL_DEP" ] || [ "$UNINSTALL" ]
do
	# separate PATH_LIST to separate directories, which uses ',' as separator
	OLD_IFS="$IFS"
	# set internal field separator to ',' 
	# since content of $PATH_LIST needs to be separated at ','
	IFS="," 
	for DIR in $PATH_LIST; do
		# build dependency path
		DEP_PATH="$PWD/$DIR/$DEP_FILE"
		# if dependency file exist parse contents
		if [ -e "$DEP_PATH" ]; then
			parse_dep "$DEP_PATH"
		else
			echo "Warn: no dependency file found for '$DIR', expected location: $DEP_PATH"
		fi
	done
	
	# handle while-loop exit conditions
	if [ "$LIST_UNINSTALL_DEP" ]; then
		# unset vars to exit while-loop
		LIST_UNINSTALL_DEP=
		echo -n "Are you sure? (y/n): "
		read -r LINE
		if [ "$LINE" = 'y' ]; then
			UNINSTALL=1
		fi	
	elif [ "$UNINSTALL" ]; then
		# unset vars to exit until-loop
		UNINSTALL=
		LIST_UNINSTALL_DEP=
	elif [ "$INSTALL" ]; then
		# unset vars to exit until-loop
		INSTALL=
	fi
done

