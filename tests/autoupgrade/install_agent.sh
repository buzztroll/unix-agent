#!/bin/bash

sed -i 's/Defaults .*requiretty//' /etc/sudoers || true
export AGENT_BASE_URL=$1
export AGENT_VERSION=$2
curl -kr 10 $AGENT_BASE_URL/installer.sh > installer.sh
echo "got the installer"
bash installer.sh -Z --loglevel DEBUG --base-path /dcm -B --url wss://this.isnot.reall.com/agentManager --extra-package-location $AGENT_BASE_URL
/etc/init.d/dcm-agent start
