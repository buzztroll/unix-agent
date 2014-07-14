#!/bin/bash

cd `dirname $0`
this_dir=`pwd`

cd ../pkg

for p in *.{deb,rpm};
do

    cmd="s3cmd put --acl-public $p s3://buzzdcmpyagent/$p"
    echo $cmd
    $cmd

done

s3cmd cp --acl-public s3://dcmagentunstable/dcm-agent-ubuntu-12.04-i386.deb s3://dcmagentunstable/dcm-agent-ubuntu-14.04-i386.deb
s3cmd cp --acl-public s3://dcmagentunstable/dcm-agent-ubuntu-12.04.deb s3://dcmagentunstable/dcm-agent-ubuntu-14.04.deb

exit 0
