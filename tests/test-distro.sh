#!/bin/bash

if [ "X$1" != "X" ]; then
    export DCM_AGENT_STORAGE_CREDS=$1
fi

DIR=`dirname $0`
cd $DIR

output_dir=$DIR/testoutput/`hostname`
mkdir -p $output_dir

pbase=`hostname`
echo "selecting the package for $pbase"

export AGENT_BASE_URL=file:////agent/pkgs/

export SYSTEM_CHANGING_TEST=1
echo "running configure"

sudo apt-get -y update
sudo apt-get -y install curl
sudo yum -y update
sudo yum -y install curl

sudo -E /agent/bin/installer.sh --cloud Amazon --url ws://enstratius.com:16309/ws --base-path /dcm

sudo -E /opt/dcm-agent/embedded/bin/nosetests dcm.agent.tests 2>&1 | tee $output_dir/nosetests.output

exit 0
