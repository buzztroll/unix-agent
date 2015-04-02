#!/bin/bash

# Bootstrapping is necessary because the installer script is 
# dynamic, downloaded from s3.

echo "source /root/dcmagent/env.sh"
echo "Contents:"
cat /root/dcmagent/env.sh
source /root/dcmagent/env.sh

echo "Setting up ssh keys"
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo $DCM_AGENT_SSH_KEY > /root/.ssh/authorized_keys
chmod 644 /root/.ssh/authorized_keys

echo "Retrieving installer."
echo "curl $AGENT_BASE_URL/installer.sh > /root/dcmagent/installer.sh"
curl $AGENT_BASE_URL/installer.sh > /root/dcmagent/installer.sh

echo "Executing installer."
cmd="/bin/bash /root/dcmagent/installer.sh --url $DCM_AGENT_URL --cloud $DCM_AGENT_CLOUD"
echo $cmd
$cmd

# apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

mv /etc/init.d/dcm-agent /root
# killall 

echo "Sleeping."
echo sleep $DCM_AGENT_PRE_START_SLEEP
sleep $DCM_AGENT_PRE_START_SLEEP

