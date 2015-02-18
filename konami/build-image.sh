#!/bin/bash

# Builds the docker container image for Konami cloud type.

DEFAULTS_FILE="./env.defaults"
OUTPUT="./env.sh"
ENV=`cat $DEFAULTS_FILE | grep export | cut -d'=' -f1 | cut -d' ' -f2`

[[ "$OUTPUT" == "" ]] && echo "This script should define OUTPUT" && exit -1
[[ "$DEFAULTS_FILE" == "" ]] && echo "This script should define DEFAULTS_FILE" && exit -1

rm -f $OUTPUT

# Resolve variables first by the DEFAULTS_FILE then 
# by the current environment.  Last one wins.

for e in $ENV; do 
    eval _$e=$( source $DEFAULTS_FILE && eval echo \$${e} )

    eval x=\$$e
    [ "$x" != "" ] && eval _$e=$x
    
    eval x=\$_$e
    echo "export $e=$x" >> $OUTPUT
done

docker build -t konamiagent .
