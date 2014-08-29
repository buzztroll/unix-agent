#!/usr/bin/env bash

# so that debian-6.0 can see the net
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

# make sure we have this..
which sudo
if [ $? -ne 0 ]; then
    echo "I think you are debian 6...installing sudo now"
    apt-get -y update
    apt-get -y install sudo
fi

# set environ vars
. /prov/envs

# check if base url is null
agenturl=$AGENT_BASE_URL
if [ "X$agenturl" = "Xnull" ]; then
    echo "You must set AGENT_BASE_URL it cannot be null"
    echo "Stopping now."
    exit 1
fi

which curl > /dev/null
if [ $? -ne 0 ]; then
    echo "Curl must be installed on your system to use this installer."
    echo "Installing now."
    sudo apt-get -y update
    sudo apt-get -y install curl
    sudo rpm -y install curl
fi

# download installer, make executable, and run
installerurl="$agenturl/installer.sh"
wget -O /prov/installer.sh $installerurl
chmod 755 /prov/installer.sh
cd /prov
./installer.sh --cloud Amazon --url ws://enstratius.com:16309/ws --base-path /dcm

# activate virualenv and run nosetests
. /opt/dcm-agent/embedded/agentve/bin/activate
/opt/dcm-agent/embedded/agentve/bin/nosetests -v dcm.agent.tests
