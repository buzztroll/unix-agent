#!/bin/bash

cd `dirname $0`
this_dir=`pwd`

if [ "X$1" == "X" ]; then
    tests="default-ubuntu-1004 default-ubuntu-1004-i386 default-ubuntu-1204 default-ubuntu-1204-i386 default-ubuntu-1310 default-ubuntu-1310-i386 default-centos-510-i386 default-centos-510 default-debian-720 default-debian-720-i386 default-debian-608 default-debian-608-i386 default-ubuntu-1404 default-ubuntu-1404-i386 default-centos-65 default-centos-65-i386"
    cd ../omnibus-dcm-agent
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

for s in $success; 
do
    echo "SUCCESS $s"
done
for f in $fail;
do
    echo "FAILED $f"
done
exit 0
