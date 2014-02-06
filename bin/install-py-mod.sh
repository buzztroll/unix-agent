#!/bin/bash

set -e

ve_path=$1
source $ve_path/bin/activate

cd `dirname $0`
cd ../
python setup.py install

exit $?
