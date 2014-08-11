
#!/bin/bash

cd `dirname $0`
this_dir=`pwd`

if [ "X$1" == "X" ]; then
    tests=`vagrant status | grep default- | awk '{ print $1 }'`
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
