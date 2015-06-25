#!/bin/bash
function help(){
    echo "
          This script is a small wrapper around a python program that upgrades the agent
          when invoked.  It is needed to install the requests library prior to running the script.
          You can instead activate the appropriate virtual environment of the agent and do
          pip install requests
          manually and then run the python script directly

          Usage: ./upgrade.sh version [ base_dir [ package_url [ upgrade_override ]]]

          --version [VERSION]        Is required and sets AGENT_VERSION env var.
          --base_dir [DIR]           Is optional and sets AGENT_BASE_DIR, default is /dcm.
          --package_url [URL]        Is optional and sets AGENT_BASE_URL, default is http://linux.stable.agent.enstratius.com
          --upgrade_override [URL]   Is optional and downloads the upgrade python program from a location other than
                                     what is specified by package_url
          --allow_unkown_certs/-Z    Is an optional flag to disable cert validation
          "
          }
cd /tmp

if [[ "X$1" == "X--help" || "X$1" == "X-h" ]]; then
        help
        exit 1
fi

. /opt/dcm-agent/embedded/agentve/bin/activate

pip install requests

chmod +x upgrade.py
echo "Running upgrade script with arguments: $@"
python upgrade.py $@