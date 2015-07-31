#!/bin/bash
function help(){
    echo "
          This script is a small wrapper around a python program that upgrades the agent
          when invoked.  It is needed to install the requests library prior to running the script.
          You can instead activate the appropriate virtual environment of the agent and do
          pip install requests
          manually and then run the python script directly

          Usage: ./upgrade.sh version [ base_dir [ package_url [ upgrade_override ]]]

          --version [VERSION]        Required and sets AGENT_VERSION env var.
          --base_dir [DIR]           Optional and sets AGENT_BASE_DIR, default is /dcm.
          --package_url [URL]        Optional and sets AGENT_BASE_URL, default is http://linux.stable.agent.enstratius.com
          --allow_unknown_certs/-Z    Optional flag to disable cert validation
          "
          }
cd /tmp

if [[ "X$1" == "X--help" || "X$1" == "X-h" ]]; then
        help
        exit 1
fi

. /opt/dcm-agent/embedded/agentve/bin/activate

pip install requests

start=`dirname $0`
cd $start
start=`pwd`

chmod +x $start/upgrade.py
echo "Running upgrade script with arguments: $@"
python $start/upgrade.py $@
