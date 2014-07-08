#!/bin/bash

if [ "X$1" != "X" ]; then
    export DCM_AGENT_STORAGE_CREDS=$1
fi

uuidgen > /vagrant/enckey
export ENCRYPTED_FILE_ENV=/vagrant/enckey

DIR=`dirname $0`
cd $DIR

output_dir=$DIR/testoutput/`hostname`
mkdir -p $output_dir

pbase=`hostname`
echo "selecting the package for $pbase"

export AGENT_BASE_URL=file:////agent/pkgs/

export SYSTEM_CHANGING_TEST=1
echo "running configure"

apt-get -y update
apt-get -y install curl
yum -y update
yum -y install curl

/agent/bin/installer.sh --cloud Amazon --url ws://enstratius.com:16309/ws --base-path /dcm

if [ $? -ne 0 ]; then
    echo "Failed to install"
    exit 1
fi

. /opt/dcm-agent/embedded/agentve/bin/activate

nosetests dcm.agent.tests 2>&1 | tee $output_dir/nosetests.output
#nosetests -svx dcm.agent.tests
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "Failed to test"
    exit 2
fi

exit 0
