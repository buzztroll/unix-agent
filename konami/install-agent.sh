#!/bin/bash

# source the environment.  This allows us to customize the build
# All environment variables that control the installer can be used
# in the env.sh file.
. /tmp/agent_install/env.sh

curl $AGENT_BASE_URL/installer.sh > /tmp/installer.sh
/bin/bash /tmp/installer.sh -I
