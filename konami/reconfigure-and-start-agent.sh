#!/bin/bash

set -e

/opt/dcm-agent/embedded/agentve/bin/dcm-agent-configure -r /dcm/etc/agent.conf --url $DCM_AGENT_URL --cloud $DCM_AGENT_CLOUD

sleep $DCM_AGENT_PRE_START_SLEEP

/etc/init.d/dcm-agent start
