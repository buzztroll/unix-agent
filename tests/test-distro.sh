#!/bin/bash

set -e

DIR=`dirname $0`
cd $DIR

pkg=/agent/pkgs/$1

output_dir=$DIR/testoutput/`hostname`
mkdir -p $output_dir

which dpkg
if [ $? -eq 0 ]; then
    dpkg -i $pkg >&1 | tee $output_dir/build.output
else
    rpm -i $pkg >&1 | tee $output_dir/build.output
fi

/opt/es-ex-pyagent/embedded/bin/nosetests -vx --tests dcm.agent.tests.integration.test_reply_receive 2>&1 | tee $output_dir/nosetests.output
