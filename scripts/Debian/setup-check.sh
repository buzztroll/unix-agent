#!/bin/bash:
# This script is used by enStratus image makers to ensure an image is
# prepared properly and to help quickly diagnose problems. It installs
# nothing, only checks a few things.

echo "===================================="
echo "Here are the contents of /"
ls -al /
echo "Here are the contents of /mnt/tmp"
ls -al /mnt/tmp
echo "here are the contents of /home"
ls -al /home
echo "===================================="
sleep 2

echo "===================================="
echo "grepping for Root in /etc/sshd/sshd_config"
grep -r Root /etc/ssh/sshd_config
echo "===================================="


for i in {zip,unzip,postfix,secure-delete,build-essential,cryptsetup};
do
        dpkg -l | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: $i} is not installed!"
        fi
done


for i in {mysql-server,python-mysqldb,python-json,mdadm};
do
        dpkg -l | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done

for i in {xfsprogs,sun-java6-jdk,ec2-{ami,api}-tools,tomcat5.5};
do
        dpkg -l | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done


for i in {sysstat,apache2,libapache2-mod-jk,haproxy,cronolog};
do
        dpkg -l | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done

for i in {linux-image-virtual,linux-virtual};
do
        dpkg -l | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done

echo "================================="
for module in {sha256,dm_crypt};
do
	modprobe ${module}
	echo "${module}" >> /etc/modules
	if [ $? != 0 ]; then
	echo "ERROR: ${module} did not install."
	echo "Check your /etc/modules file!"
	exit 127
	fi
done

echo "=====/etc/modules:=============="
cat /etc/modules
echo ""
echo ""
echo ""
echo ""

echo "Checking for running process that shouldn't be."
for pkg in {mysql,avahi,apache2};
do
        pgrep ${pkg}
        if [ $? = 0 ]; then
                echo "Why is ${pkg} running?"
        fi
done

echo "===================================="
echo "Checking for auhtorized_keys files."
find / -iname "authorized_keys"
echo " "

echo "===================================="
echo "Here's the output of netstat -tnlup"
netstat -tnlup
echo "===================================="

#chown root.root /lib
#chown root.root /lib/modules

shasum /enstratus/bin/setupEncryption
shasum /enstratus/bin/openEncryption

echo "Looking for p335"

grep -r p335 /etc
grep -r c100 /etc
