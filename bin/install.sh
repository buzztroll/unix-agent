#!/bin/bash

c=`dirname $0`
cd $c
pwd
python install.py ${@}
exit $?
