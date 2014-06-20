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
    kitchen converge $t
    if [ $? -eq 0 ]; then
        success="$t $success"
        pkg=`ls -tC1 ../pkg/$t/*.deb 2> /dev/null | head -n 1`
        if [ "X$pkg" == "X" ]; then
            suffix=".rpm"
            pkg=`ls -tC1 ../pkg/$t/*.rpm 2> /dev/null | head -n 1`
        else
            suffix=".deb"
        fi

         if [ "X$pkg" != "X" ]; then
            x=`echo $t | sed "s/default-//"`
            echo $x
            keyname="dcm-agent-$x$suffix"
            cp $pkg ../pkg/$keyname
            s3cmd put $x s3://agentbucket/$keyname
            echo $?
        fi
    else
        fail="$t $fail"
    fi
    kitchen destroy $t
done

echo "SUCCEDED $success"
echo "FAILED $fail"

exit 0
