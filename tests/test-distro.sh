#!/bin/bash

set -e

if [ "X$2" != "X" ]; then
    export DCM_AGENT_STORAGE_CREDS=$2
fi

DIR=`dirname $0`
cd $DIR

output_dir=$DIR/testoutput/`hostname`
mkdir -p $output_dir

pbase=`hostname`
echo "selecting the package for $pbase"
pkg_dir=$1

echo "installing the package $pkg"
which dpkg
if [ $? -eq 0 ]; then
    pkg=`ls -C1 $pkg_dir/*.deb`
    sudo dpkg -i $pkg >&1 | tee $output_dir/build.output
else
    pkg=`ls -C1 $pkg_dir/*.rpm`
    sudo rpm -i $pkg >&1 | tee $output_dir/build.output
fi

export SYSTEM_CHANGING_TEST=1

echo "running configure"
sudo /opt/dcm-agent/embedded/bin/dcm-agent-configure --cloud Amazon --url ws://enstratius.com:16309/ws --base-path /dcm

sudo /opt/dcm-agent/embedded/bin/nosetests dcm.agent.tests 2>&1 | tee $output_dir/nosetests.output

exit 0
