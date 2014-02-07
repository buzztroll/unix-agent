#!/bin/bash

set -e

ve_path=$1
source $ve_path/bin/activate

cd `dirname $0`
cd ../
pip install -r requirements.txt
pip install -r test-requirements.txt
python setup.py install

exit $?
