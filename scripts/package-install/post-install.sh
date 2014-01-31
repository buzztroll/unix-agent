#!/usr/bin/env bash
#
# Copyright 2010-2013 Enstratius, Inc.
#
# post-install - Set privileges of directories and files, make init scripts, run enstratius service.
# 
# This software is part of the Enstratius Cloud Management System. Only 
# authorized licensees of Enstratius may use this software and only
# in the context of Enstratius-managed virtual servers and machine images. 
# Unauthorized copying or distribution of this software is strictly prohibited.
# Authorized licensees may copy this software onto any machine images
# and/or virtual hosts being managed by the Enstratius system as needed.

PATH=/bin:${PATH}

if [ -z "$JAVA_HOME" ] ; then
    JAVA_HOME=""
fi

set -u

# Set Java environment variable.
OPEN_JDK_DIRS="/usr/lib/jvm/java-1.6.0-openjdk.x86_64 /usr/lib/jvm/jre-1.6.0-openjdk.x86_64 /usr/lib/jvm/java-6-openjdk-amd64 /usr/lib/jvm/java-1.6.0-openjdk" 
ORACLE_JDK_DIRS="/usr/lib/jvm/java-6-sun /usr/lib/jvm/java-1.5.0-sun /usr/lib/j2sdk1.5-sun /usr/lib/j2sdk1.4-sun /usr/lib/j2sdk1.3-sun "
IBM_JDK_DIRS="/usr/lib/j2sdk1.5-ibm /usr/lib/j2sdk1.4-ibm /usr/lib64/jvm/java-1.6.0-ibm /usr/lib/jvm/java-1.6.0-ibm"
SOME_DIRS="/usr/java/jdk1.6.0_02 /usr/lib/j2sdk1.4-blackdown /usr/lib/j2se/1.4 /usr/lib/j2sdk1.3-blackdown /usr/lib/jvm/java-gcj /usr/lib/kaffe "
OTHER_DIRS=$( echo /usr/java/jdk1.{6,7}.0_{13..64} )
JDK_DIRS=$OPEN_JDK_DIRS" "$ORACLE_JDK_DIRS" "$IBM_JDK_DIRS" "$SOME_DIRS" "$OTHER_DIRS

for jdir in $JDK_DIRS; do
	if [ -r "$jdir/bin/javac" -a -z "${JAVA_HOME}" ]; then
		JAVA_HOME_TMP="$jdir"
		if [ -r "$jdir/bin/jdb" ]; then
		    JAVA_HOME="$JAVA_HOME_TMP"
		fi
    fi
done

if [ -z "$JAVA_HOME" ] ; then
	echo "no JDK found - please set JAVA_HOME"
	exit 13
fi

export JAVA_HOME

javaTest="${JAVA_HOME}/bin/javac"

sed "s|javaHome|$JAVA_HOME|g" /enstratus/bin/enstratus-service > /var/tmp/enstratus-service
mv /var/tmp/enstratus-service /enstratus/bin/enstratus-service

echo "Setting enstratus permissions..."
mkdir -p /enstratus/custom/bin
mkdir /enstratus/home
chown -R enstratus:enstratus /enstratus
chmod 775 /enstratus
chmod 750 /enstratus/bin
chmod 550 /enstratus/bin/*
chmod 755 /enstratus/custom/bin
chmod -R 750 /enstratus/home
chown -R enstratus:enstratus /enstratus/home
chmod 750 /enstratus/cfg
chmod 640 /enstratus/cfg/*
chmod 754 /enstratus/ws/tomcat/bin/*.sh
echo "Done."

echo "Setting /mnt/tmp and /tmp permissions..."
mkdir -p /mnt/tmp 2>&1 > /dev/null
chown -R enstratus:enstratus /mnt/tmp 2>&1 > /dev/null
chown root:root /tmp 2>&1 > /dev/null
chmod 1777 /tmp 2>&1 > /dev/null
echo "Done."

# IBM JDK uses IbmX509 for certifacte encoding algorithm.
if [[ ${JAVA_HOME} == *ibm* ]]; then
	echo "Setting IBM X509 as certificate encoding algorithm..."
	sed -i 's/SunX509/IbmX509/' /enstratus/ws/tomcat/conf/server.xml
	echo "Done."
fi

echo "Adding user to sudoers..."

# Update sudoers.
if [ -d /etc/sudoers.d ]; then
	# For distros that have the latest sudo package which uses sudoers.d directory.
	grep -q '#includedir /etc/sudoers.d' /etc/sudoers
	if [ $? -ne 0 ]; then
		echo "#includedir /etc/sudoers.d" >> /etc/sudoers
	fi
	sed -i "/enstratus/d" /etc/sudoers
	echo "Defaults:enstratus !requiretty" > /tmp/ens-sudoers
	echo "enstratus ALL=(ALL) NOPASSWD: ALL" >> /tmp/ens-sudoers
	chown root:root /tmp/ens-sudoers
	chmod 0440 /tmp/ens-sudoers
	mv /tmp/ens-sudoers /etc/sudoers.d/enstratus
elif [ -f /etc/sudoers ]; then
	# For distros that do not have the latest sudo package.
	chmod u+w /etc/sudoers
	sed -i "/enstratus/d" /etc/sudoers
	echo "Defaults:enstratus !requiretty" >> /etc/sudoers
	echo "enstratus ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
	chmod u-w /etc/sudoers
else
	echo "error. sudoers not found."
	exit 55
fi
echo "Done."

echo "Attempting to install startup scripts..."

echo "#!/bin/bash" > /etc/init.d/tomcat-enstratus
echo "#!/bin/bash" > /etc/init.d/enstratus
if [ -f /usr/sbin/update-rc.d ] ; then

	echo "#" >> /etc/init.d/tomcat-enstratus
	echo "### BEGIN INIT INFO" >> /etc/init.d/tomcat-enstratus
	echo "# Provides:          tomcat-enstratus" >> /etc/init.d/tomcat-enstratus
	echo "# Required-Start:    \$remote_fs \$syslog" >> /etc/init.d/tomcat-enstratus
	echo "# Required-Stop:     \$remote_fs \$syslog" >> /etc/init.d/tomcat-enstratus
	echo "# Should-Start:      \$network \$named" >> /etc/init.d/tomcat-enstratus
	echo "# Should-Stop:       \$network \$named" >> /etc/init.d/tomcat-enstratus
	echo "# Default-Start:     2 3 4 5" >> /etc/init.d/tomcat-enstratus
	echo "# Default-Stop:      0 1 6" >> /etc/init.d/tomcat-enstratus
	echo "# Short-Description: Starts and stops the agent" >> /etc/init.d/tomcat-enstratus
	echo "# Description:       Starts and stops the agent Tomcat service." >> /etc/init.d/tomcat-enstratus
	echo "### END INIT INFO" >> /etc/init.d/tomcat-enstratus
	cat /enstratus/bin/tomcat-enstratus >> /etc/init.d/tomcat-enstratus
	
   	echo "#" >> /etc/init.d/enstratus
	echo "### BEGIN INIT INFO" >> /etc/init.d/enstratus
	echo "# Provides:          enstratus" >> /etc/init.d/enstratus
	echo "# Required-Start:    \$remote_fs \$syslog" >> /etc/init.d/enstratus
	echo "# Required-Stop:     \$remote_fs \$syslog" >> /etc/init.d/enstratus
	echo "# Should-Start:      \$network \$named" >> /etc/init.d/enstratus
	echo "# Should-Stop:       \$network \$named" >> /etc/init.d/enstratus
	echo "# Default-Start:     2 3 4 5" >> /etc/init.d/enstratus
	echo "# Default-Stop:      0 1 6" >> /etc/init.d/enstratus
	echo "# Short-Description: Start and stop any services pre-installed on an AMI or after a reboot" >> /etc/init.d/enstratus
	echo "# Description:       Generally makes sure that all Enstratius-managed services on a system" >> /etc/init.d/enstratus
	echo "#                    are clearly shutdown whenever the system comes down" >> /etc/init.d/enstratus
	echo "### END INIT INFO" >> /etc/init.d/enstratus
	cat /enstratus/bin/enstratus >> /etc/init.d/enstratus
	
	chmod 755 /etc/init.d/tomcat-enstratus
	chmod 755 /etc/init.d/enstratus
	
	update-rc.d tomcat-enstratus defaults
	update-rc.d enstratus defaults
	
elif [ -x /sbin/chkconfig ] ; then

	echo "# chkconfig: 2345 60 40" >> /etc/init.d/tomcat-enstratus
	echo "# description: Manages the Enstratius agent." >> /etc/init.d/tomcat-enstratus
	cat /enstratus/bin/tomcat-enstratus >> /etc/init.d/tomcat-enstratus
	
	echo "# chkconfig: 2345 60 40" >> /etc/init.d/enstratus
	echo "# description: Manages the Enstratius agent." >> /etc/init.d/enstratus
	cat /enstratus/bin/enstratus >> /etc/init.d/enstratus
	
	chmod 755 /etc/init.d/tomcat-enstratus
	chmod 755 /etc/init.d/enstratus
	
	/sbin/chkconfig --add tomcat-enstratus	
	/sbin/chkconfig --add enstratus	
	
else
	echo "Could not identify startup protocols. Contact Enstratius support at support@enstratius.com."
	exit 90
fi
echo "Done."

echo "======================================================="
echo "The installation of the Enstratius Agent has completed."
echo "To start the agent, run the following command."
echo "/etc/init.d/tomcat-enstratus start"
echo "-------------------------------------------------------"
echo "Please make sure to"
echo "1. open TCP port 2003 for agent communication."
echo "2. disable SELinux."
echo "======================================================="
exit 0
