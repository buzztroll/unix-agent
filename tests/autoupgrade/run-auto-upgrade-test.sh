#!/bin/bash

which yum
if [ $? -ne 0 ]; then
    apt-get -y update
    apt-get -y install curl python-virtualenv python-dev libsqlite3-dev
else
#    yum -y update
    yum install -y curl python-devel python-setuptools sqlite-devel
    yum groupinstall -y development
    easy_install virtualenv
    easy_install pip
fi

set -e
start_dir=`dirname $0`
cd $start_dir

FIRST_PACKAGE_URL=$1
FIRST_PACKAGE_NAME=`basename $FIRST_PACKAGE_URL`
UPGRADE_PACKAGE=$2
EXPECTED_VERSION=$3

cp -a /agent/src /root
cd /root/src/
pip install -r requirements.txt
pip install -r test-requirements.txt
python setup.py install
cd -

curl $FIRST_PACKAGE_URL > $FIRST_PACKAGE_NAME
export AGENT_LOCAL_PACKAGE=file:///$start_dir/$FIRST_PACKAGE_NAME
cd /tmp
/agent/bin/installer.sh --cloud Amazon --url ws://127.0.0.1:9000/ws

/etc/init.d/dcm-agent start
sleep 1
ps -e | grep dcm

cd $start_dir
python test_auto_upgrade.py $EXPECTED_VERSION $UPGRADE_PACKAGE
if [ $? -ne 0 ]; then
    echo "The test failed!"
    exit 2
fi
ps -e | grep dcm

echo "Success"
exit 0
