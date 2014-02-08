#!/bin/bash

if [ "X$1" == "X" ]; then
    tests="ubuntu-12.04 ubuntu-10.04 centos-5.10 centos-6.5"
else
    tests=$1
fi

for t in $tests;
do
    fname=`echo $t | sed 's/-/\./'`

    p=`ls -tc1 ../omnibus-es-ex-pyagent/pkg/*$fname*.deb`
    if [ $? -eq 0 ]; then 
        p=`echo $p | head -n 1`
        pkg_name=`basename $p`
        export ES_AGENT_PKG_NAME=$pkg_name

        echo $ES_AGENT_PKG_NAME
        vagrant up $t
    else
       echo "No package found for $t.  Skipping this test"
    fi
done
