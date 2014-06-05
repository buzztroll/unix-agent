#!/bin/bash

set -e

DIR=`dirname $0`
cd $DIR

pkg_base=$1

if [ -e /agent/pkgs/$pkg_base ]; then
    pkg=/agent/pkgs/$pkg_base
else
    echo "The package $1 was not found"
    exit 1
fi

output_dir=$DIR/testoutput/`hostname`
mkdir -p $output_dir

which dpkg
if [ $? -eq 0 ]; then
    dpkg -i $pkg >&1 | tee $output_dir/build.output
else
    rpm -i $pkg >&1 | tee $output_dir/build.output
fi

export SYSTEM_CHANGING_TEST=1
/opt/dcm-agent/embedded/bin/dcm-agent-configure --cloud Amazon --url ws:/enstratius.com:16309/ws --base-path /dcm

/opt/dcm-agent/embedded/bin/nosetests dcm.agent.tests 2>&1 | tee $output_dir/nosetests.output
