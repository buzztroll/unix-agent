#!/bin/bash

if [ "X$1" == "X" ]; then
    tests="ubuntu-12.04 ubuntu-14.04 ubuntu-11.04"
else
    tests=$1
fi

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
