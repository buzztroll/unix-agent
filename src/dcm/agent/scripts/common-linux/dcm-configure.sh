#!/usr/bin/env bash

set -u
set -e

BASENAME=`basename $0`
DIRNAME=`dirname $0`
. $DIRNAME/variables.sh
. "$DIRNAME/common_mod"

# backup any existing configuration files
conf_files="$DCM_BASEDIR/etc/agent.conf $DCM_BASEDIR/etc/plugin.conf $DCM_BASEDIR/etc/logging.yaml"

suffix="backup."`/bin/date +%s`
for conf in $conf_files
do
    if [ -e $conf ]; then
        echo "Backing up $conf to $conf.$suffix"
        cp $conf $conf.$suffix
    fi
done

echo "Create the configuration file"
env -i /opt/dcm-agent/bin/dcm-agent-configure $@ -i -r $DCM_BASEDIR/etc/agent.conf
if [ $? -ne 0 ]; then
    echo "The default configuration failed"
    exit 1
fi
echo "Done"
