#!/bin/bash

cd `dirname $0`
this_dir=`pwd`

if [ "X$1" == "X" ]; then
    cd ../omnibus-dcm-agent
    tests=`kitchen list -b`
else
    tests=$@
fi

cd $this_dir

success=""
fail=""
for t in $tests;
do
    pkg=`ls -tC1 ../pkg/$t/*.deb 2> /dev/null | head -n 1`
    if [ "X$pkg" == "X" ]; then
        suffix=".rpm"
        pkg=`ls -tC1 ../pkg/$t/*.rpm 2> /dev/null | head -n 1`
        echo $t
    else
        suffix=".deb"
    fi

     if [ "X$pkg" != "X" ]; then
        x=`echo $t | sed "s/default-//"`
        keyname="dcm-agent-$x$suffix"
        echo $keyname
        cp $pkg ../pkg/$keyname
        s3cmd put $x s3://agentbucket/$keyname
    fi
done

exit 0
