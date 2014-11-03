#!/bin/bash

# source the environment.  This allows us to customize the build
# All environment variables that control the installer can be used
# in the env.sh file.
. /tmp/agent_install/env.sh

mkdir /root/.ssh
chmod 700 /root/.ssh
echo $DCM_AGENT_SSH_KEY > /root/.ssh/authorized_keys
echo $DCM_AGENT_SSH_KEY > /home/ubuntu/.ssh/authorized_keys
chmod 644 /root/.ssh/authorized_keys

curl $AGENT_BASE_URL/installer.sh > /tmp/installer.sh
/bin/bash /tmp/installer.sh -I
