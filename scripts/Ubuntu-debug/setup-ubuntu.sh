#!/bin/bash

set -u

apt-get update
apt-get upgrade -y
dpkg-reconfigure tzdata

for pkg in {zip,unzip,postfix,secure-delete,build-essential,cryptsetup};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
		echo "ERROR: ${pkg} did not install!"
		exit 127
	fi
done

for pkg in {mysql-server,python-mysqldb,python-json,mdadm};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
	echo "ERROR: ${pkg} did not install!"
	exit 127
	fi
done

for pkg in {xfsprogs,sun-java6-jdk,tomcat6,ec2-api-tools};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
	echo "ERROR: ${pkg} did not install!"
	exit 127
	fi
done



for pkg in {sysstat,apache2,libapache2-mod-jk,haproxy,cronolog};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
	echo "ERROR: ${pkg} did not install!"
	exit 127
	fi
done

for pkg in {linux-image-virtual,linux-virtual};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
	echo "ERROR: ${pkg} did not install!"
	exit 127
	fi
done

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

# George loves emacs; uncomment if you love emacs too
#apt-get install -y emacs22-nox

#64-bit instances only:
#ln -s /usr/lib/jvm/java-1.5.0-sun/jre/lib/amd64/libmlib_image.so /usr/lib

service apache2 stop
service mysql stop
service tomcat6 stop
service postfix stop
update-rc.d -f apache2 remove
update-rc.d -f postfix remove
update-rc.d -f mysql remove
rm -f /etc/init.d/mysql
update-rc.d -f tomcat6 remove

#remove avahi
service avahi-daemon stop
rm /etc/init.d/avahi-daemon
update-rc.d avahi-daemon remove
apt-get -y remove --purge avahi-daemon
apt-get -y autoremove

usermod --groups ossec enstratus
