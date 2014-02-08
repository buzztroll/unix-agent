#!/bin/bash

set -e

DIR=`dirname $0`
cd $DIR

pkg=/agent/pkgs/$1

output_dir=$DIR/testoutput/`hostname`
mkdir -p $output_dir

which dpkg
if [ $? -eq 0 ]; then
    dpkg -i $pkg 
else
    rpm -i $pkg 
fi


