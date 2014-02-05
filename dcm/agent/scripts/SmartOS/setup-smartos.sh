#!/bin/bash

set -u

pkgin -y update
pkgin -y full-upgrade

req_packages=(
coreutils
findutils
gcc-compiler
gmake
gsed
gtar-base
less
postfix
py27-mysqldb
sun-jdk6
unzip
vim
zip
)

for pkg in ${req_packages[@]};
do
	pkgin -y install ${pkg}
	if [ $? != 0 ]; then
		echo "ERROR: ${pkg} did not install!"
		exit 127
	fi
done

wget http://www.ossec.net/files/ossec-hids-2.6.tar.gz
tar -xzf ossec-hids-2.6.tar.gz
cd ossec-hids-2.6
./install.sh

usermod -G ossec enstratus
 
