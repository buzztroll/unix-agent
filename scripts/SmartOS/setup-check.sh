#!/bin/bash
# This script is used by enStratus image makers to ensure an image is
# prepared properly and to help quickly diagnose problems. It installs
# nothing, only checks a few things.

echo "===================================="
echo "Here are the contents of /"
ls -al /
echo "Here are the contents of /var/enstratus/tmp"
ls -al /var/enstratus/tmp
echo "here are the contents of /home"
ls -al /home
echo "===================================="
sleep 2

echo "===================================="
echo "grepping for Root in /etc/sshd/sshd_config"
grep -r Root /etc/ssh/sshd_config
echo "===================================="

req_packages=(
coreutils
findutils
gcc-compiler
gmake
gsed
gtar-base
postfix
py27-mysqldb
sun-jdk6
unzip
vim
zip
)

for i in ${req_packages[@]};
do
        pkgin list | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: $i} is not installed!"
        fi
done

echo "Checking for running process that shouldn't be."
for pkg in {mysql,httpd};
do
        pgrep ${pkg}
        if [ $? = 0 ]; then
                echo "Why is ${pkg} running?"
        fi
done

echo "===================================="
echo "Checking for authorized_keys files."
find / -iname "authorized_keys"
echo " "

echo "===================================="
echo "Here's the output of netstat -np"
netstat -np
echo "===================================="

shasum /opt/local/enstratus/bin/setupEncryption
shasum /opt/local/enstratus/bin/openEncryption
