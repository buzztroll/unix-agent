#!/bin/bash

p=`ls -tc1 *ubuntu.12*.deb | head -n 1`
if [ $? -eq 0 ]; then
    echo $p
    pkg_name=`basename $p`

    dpkg -i $pkg_name
    /opt/es-ex-pyagent/embedded/bin/dcm-agent-configure -v -u http://172.16.129.19:76309 --cloud OpenStack
else
    echo "No package found"
    pwd
    ls
    exit 1
fi
