#!/bin/bash 

dt=`date +%s`
packages=`kitchen list -b`

if [ -e "pkg" ]; then
    mv pkg pkg.$dt
fi

for p in $packages; 
do
    echo "Making the package for $p..."
    kitchen converge $p
    for f in pkg/*;
    do
        mv $f $f.$p
    done
    kitchen destroy
    echo "...done"
done
