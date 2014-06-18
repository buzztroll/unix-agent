#!/bin/bash

cd `dirname $0`
this_dir=`pwd`

cd ../pkg

for d in *;
do
    pkg=`ls -tC1 ../pkg/$d/*.deb 2> /dev/null | head -n 1`
    if [ "X$pkg" == "X" ]; then
         suffix=".rpm"
         pkg=`ls -tC1 ../pkg/$d/*.rpm 2> /dev/null | head -n 1`
     else
         suffix=".deb"
     fi
     if [ "X$pkg" != "X" ]; then
         x=`echo $d | sed "s/default-//"`
         x=`echo $x | sed 's/\.vagrantup.com//'`
         keyname="dcm-agent-$x$suffix"
         if [ "X$1" == "X" ]; then
             s3cmd put --acl-public $pkg s3://agentbucket/$keyname
         else
             echo $pkg
         fi
     fi
done

exit 0
