#!/bin/bash
# This script is used by Enstratius image makers to ensure an image is
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

echo "Checking for srm"
found=$( which srm )
if [ $? = 0 ]
then
        echo "found srm at $found"
else
        echo "no srm found"
fi

echo "-----"

gotJava=$( which java )
if [ $? = 0 ]
then
        echo "Found java at $gotJava"
else
        echo "Dude, where's my Java?"
fi

echo "===================================="

$gotJava -version

if [ $? = 0 ]
then
        echo "===== JAVA OK ====="
else
        echo "===== Could be a Java Problem ====="
fi

for i in {zip,unzip,postfix,gcc,cryptsetup-luks};
do
        rpm -qa | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: $i} is not installed!"
        fi
done

for i in {mysql-server,MySQL-python,python-json,mdadm};
do
        rpm -qa | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done

for i in {xfsprogs,tomcat6};
do
        rpm -qa | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done


for i in {sysstat,httpd,haproxy,cronolog};
do
        rpm -qa | grep ${i}
        if [ $? != 0 ]; then
                echo "ERROR: ${i} is not installed!"
        fi
done

#for i in {linux-image-virtual,linux-virtual};
#do
#        rpm -qa | grep ${i}
#        if [ $? != 0 ]; then
#                echo "ERROR: ${i} is not installed!"
#        fi
#done

echo "================================="
for module in {sha256,dm_crypt};
do
        /sbin/modprobe ${module}
        echo "${module}" >> /etc/modules
        if [ $? != 0 ]; then
        echo "ERROR: ${module} did not install."
        echo "Check your /etc/modules file!"
        exit 127
        fi
done

cat /etc/modules

for pkg in {mysql,avahi,httpd};
do
        pgrep ${pkg}
        if [ $? = 0 ]; then
                echo "Why is ${pkg} running?"
        fi
done

echo "===================================="
echo "Checking for authorized_keys files."
find / -iname "authorized_keys"
echo "===================================="

echo "===================================="
echo "Here's the output of netstat -tnlup"
netstat -tnlup
echo "===================================="

sha1sum /enstratus/bin/setupEncryption
sha1sum /enstratus/bin/openEncryption

echo "Looking for p335"

#grep -r p335 /etc
#grep -r c100 /etc
