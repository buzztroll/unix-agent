#!/bin/bash

PIDFILE=/dcm/dcm-agent.pid

/usr/bin/nohup /opt/dcm-agent/embedded/agentve/bin/dcm-agent -c /dcm/etc/agent.conf 0<&- &>/dev/null &
PID=$!
if [ $? -ne 0 ]; then
    echo "Failed to start"
    exit 1
fi

echo $PID > $PIDFILE
