#!/bin/bash

# https://community.openhab.org/t/iphone-presence-detection-with-hping3-and-arp/18171/28

# detect iphone by IP and MAC address.
# use MAC address too, to prevent false positives if IP might change
# return ON or OFF so output can be directly bound to a switch item

# number of retries, less is faster, but less accurate
MAXRETRIES=20

# exit immediately if no parameters supplied
if [ $# -lt 2 ]
	then
		echo "UNDEF"
		exit 1
fi

# Set variables
IP=$1
MAC=$2

COUNT=0
while [ ${COUNT} -lt ${MAXRETRIES} ];
do
	ip neigh flush dev eth0 ${IP}
	hping3 -q -2 -c 10 -p 5353 -i u1 ${IP} >/dev/null 2>&1
	sleep 1

	# Only arp specific device, grep for a mac-address
	STATUS=`/usr/sbin/arp -an ${IP} | awk '{print $4}' | grep "${MAC}"`

	if [ ${#STATUS} -eq 17 ]; then
		# exit when phone is detected
		echo "${IP} ON"
		exit 0
	fi
	let COUNT=COUNT+1
	sleep .1
done

# consider away if reached max retries
echo "${IP} OFF"

