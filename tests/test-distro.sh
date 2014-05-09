#!/bin/bash

set -e

DIR=`dirname $0`
cd $DIR

pkg_base=$1

p=`ls -tc1 /agent/pkgs/*$pkg_base*.deb`
if [ $? -eq 0 ]; then
    pkg=`echo $p | head -n 1`
else
   echo "No package found for $t.  Skipping this test"
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
/opt/dcm-agent/embedded/bin/nosetests -vx --tests dcm.agent.tests.integration.test_reply_receive 2>&1 | tee $output_dir/nosetests.output
