#!/bin/bash

script_to_run=$1

cd `dirname $0`
start_dir=`pwd`

wait_for_list=""
for distro_to_build in builder*;
do
    $script_to_run $distro_to_build &
    pid=$!
    wait_for_list="$wait_for_list $distro_to_build:$pid"
    sleep 30
done

SUCCESS=""
ERROR=""
rc=0
for job in $wait_for_list;
do
    pid=`echo $job | awk -F : '{ print $2 }'`
    name=`echo $job | awk -F : '{ print $1 }'`
    wait $pid
    if [ $? -eq 0 ]; then
        SUCCESS="$SUCCESS $name"
    else
        ERROR="$ERROR $name"
        rc=1
    fi
    echo "XXX DONE $name"
done

echo "Success: $SUCCESS"
echo "Error: $ERROR"
exit $rc
