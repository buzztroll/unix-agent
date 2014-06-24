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

exit 0
