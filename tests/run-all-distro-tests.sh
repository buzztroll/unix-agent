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
    vagrant up $t
    if [ $? -eq 0 ]; then
        success="$t $success"
    else
        fail="$t $fail"
    fi
    echo $?
    vagrant destroy -f $t
done

echo "SUCCEDED $success"
echo "FAILED $fail"

exit 0
