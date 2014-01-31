#!/usr/bin/env bash

# Copyright 2010-2013 Enstratius, Inc.
#
# install - Installs Enstratius on a UNIX system
# 
# This software is part of the Enstratius Cloud Management System. Only 
# authorized licensees of Enstratius may use this software and only
# in the context of Enstratius-managed virtual servers and machine images. 
# Unauthorized copying or distribution of this software is strictly prohibited.
# Authorized licensees may copy this software onto any machine images
# and/or virtual hosts being managed by the Enstratius system as needed.
#
# FUNCTION
# Call this script to install Enstratius on a UNIX system.

if [ -z "$JAVA_HOME" ] ; then
    JAVA_HOME=""
fi

set -u

CMD=${0}
BASEDIR=`dirname ${CMD}`
INSTALL=`basename ${CMD}`

if [ $# -lt 1 ] ; then
    echo "Syntax: install.sh [Amazon|Atmos|ATT|Azure|Bluelock|CloudCentral|CloudSigma|CloudStack|Eucalyptus|GoGrid|Google|IBM|Joyent|OpenStack|Rackspace|ServerExpress|Terremark|VMware] [production|staging] [provisioningProxyIP:port]"
    exit 1
elif [ $# -lt 2 ] ; then
    ESENV=production
    CLOUD=Amazon
    case $1 in
        Amazon) CLOUD=Amazon ;;
        Atmos) CLOUD=Atmos ;;
        ATT) CLOUD=ATT ;;
        Azure) CLOUD=Azure ;;
        Bluelock) CLOUD=Bluelock ;;
        CloudCentral) CLOUD=CloudCentral ;;
        CloudSigma) CLOUD=CloudSigma ;;
        CloudStack) CLOUD=CloudStack ;;
        Eucalyptus) CLOUD=Eucalyptus ;;
        GoGrid) CLOUD=GoGrid ;;
        Google) CLOUD=Google ;;
        Joyent) CLOUD=Joyent ;;
        OpenStack) CLOUD=OpenStack ;;
        Rackspace) CLOUD=Rackspace ;;
        ServerExpress) CLOUD=ServerExpress ;;
        Terremark) CLOUD=Terremark ;;
        VMware) CLOUD=VMware ;;
        production) ESENV=production ;;
        staging) ESENV=staging ;;
        *) CLOUD=$1 ;;
    esac
    PROXY="#provisioningProxy=255.255.255.255:3302"
elif [ $# -lt 3 ] ; then
    CLOUD=$1
    ESENV=$2
    case $1 in
        production) CLOUD=$2; ESENV=$1 ;;
        staging) CLOUD=$2; ESENV=$1 ;;
        *) CLOUD=$1; ESENV=$2 ;;
    esac
    PROXY="#provisioningProxy=255.255.255.255:3302"
elif [ $# -lt 4 ] ; then
    CLOUD=$1
    ESENV=$2
    case $1 in
        production) CLOUD=$2; ESENV=$1 ;;
        staging) CLOUD=$2; ESENV=$1 ;;
        *) CLOUD=$1; ESENV=$2 ;;
    esac
	PROXY="provisioningProxy=$3"
else
    echo "Syntax: install.sh [Amazon|Atmos|ATT|Azure|CloudCentral|CloudSigma|CloudStack|Eucalyptus|GoGrid|Google|OpenStack|Rackspace|ServerExpress|Terremark|VMware] [production|staging] [provisioningProxyIP:port]"
    exit 1
fi

echo "Installing enStratus Agent for $CLOUD..."

SOME_DIRS="/usr/lib/jvm/java-6-openjdk-amd64/ /usr/lib/jvm/java-1.6.0-openjdk /usr/lib/jvm/java-6-sun /usr/java/jdk1.6.0_02 /usr/lib/jvm/java-1.5.0-sun /usr/lib/j2sdk1.5-sun /usr/lib/j2sdk1.5-ibm /usr/lib/j2sdk1.4-sun /usr/lib/j2sdk1.4-blackdown /usr/lib/j2se/1.4 /usr/lib/j2sdk1.4-ibm /usr/lib/j2sdk1.3-sun /usr/lib/j2sdk1.3-blackdown /usr/lib/jvm/java-gcj /usr/lib/kaffe"

OTHER_DIRS=$( echo /usr/java/jdk1.6.0_{13..64} )

JDK_DIRS=$SOME_DIRS" "$OTHER_DIRS

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

if [ ! -x "$javaTest" ] ; then
	echo "You must install a valid JDK and point JAVA_HOME to that JDK."
	echo "Ubuntu: apt-get install -y sun-java6-jdk"
	exit 11
fi

perl -v > /dev/null 2>&1

if [ $? != 0 ] ; then
	echo "Perl must be installed on this system in order for enStratus to run."
	exit 12
fi

echo "Creating enstratus directory at /enstratus..."
if [ ! -d /enstratus ] ; then
	mkdir /enstratus
	if [ $? != 0 ] ; then
		echo "Could not create /enstratus directory. Are you running this as root?"
		exit 30
	fi
fi
echo "Done."

echo "Creating enstratus user and group..."
id enstratus 2> /dev/null
if [ $? != 0 ] ; then
	groupadd enstratus 2> /dev/null
	if [ $? != 0 ] ; then
		echo "Failed to add enstratus group."
		exit 40
	fi
	useradd -d /enstratus/home -g enstratus -s /bin/false -m enstratus 2> /dev/null
	if [ $? != 0 ] ; then
		echo "Failed to add enstratus user. Please add an enstratus user manually and restart the script."
		echo "The script will take over gracefully when you restart it."
		exit 41
	fi
fi
echo "Done."

echo "Setting enstratus permissions..."
chown enstratus:enstratus /enstratus
chmod 775 /enstratus
echo "Done."

echo "Installing enStratus into /enstratus..."
cp -R ${BASEDIR}/* /enstratus
rm -f /enstratus/${INSTALL}
rm -f /enstratus/upgrade.sh

sudo sed "s|javaHome|$JAVA_HOME|g" /enstratus/bin/enstratus-service > /var/tmp/enstratus-service
sudo mv /var/tmp/enstratus-service /enstratus/bin/enstratus-service

echo "cloud=${CLOUD}" > /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg
echo "environment=${ESENV}" >> /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg
echo "$PROXY" >> /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg

chown -R enstratus:enstratus /enstratus
chmod 750 /enstratus/bin
chmod 550 /enstratus/bin/*
chmod 755 /enstratus/custom/bin
chmod -R 750 /enstratus/home
chmod 750 /enstratus/cfg
chmod 640 /enstratus/cfg/*
chmod 754 /enstratus/ws/tomcat/bin/*.sh
echo "Done.";

echo "Adding enStratus user to /etc/sudoers..."
chmod u+w /etc/sudoers
echo "%enstratus    ALL=(ALL) NOPASSWD: ALL" | tee -a /etc/sudoers
perl -ni -e 'print unless /requiretty/' /etc/sudoers
chmod u-w /etc/sudoers
echo "Done."

echo "Attempting to install startup scripts..."

echo "#!/usr/bin/env bash" > /etc/init.d/tomcat-enstratus
echo "#!/usr/bin/env bash" > /etc/init.d/enstratus
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
	echo "# Short-Description: Starts and stops the enStratus agent" >> /etc/init.d/tomcat-enstratus
	echo "# Description:       Starts and stops the enStratus agent Tomcat service." >> /etc/init.d/tomcat-enstratus
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
	echo "# Description:       Generally makes sure that all enStratus-managed services on a system" >> /etc/init.d/enstratus
	echo "#                    are clearly shutdown whenever the system comes down" >> /etc/init.d/enstratus
	echo "### END INIT INFO" >> /etc/init.d/enstratus
	cat /enstratus/bin/enstratus >> /etc/init.d/enstratus
	
	chmod 755 /etc/init.d/tomcat-enstratus
	chmod 755 /etc/init.d/enstratus
	
	update-rc.d tomcat-enstratus defaults
	update-rc.d enstratus defaults
	
elif [ -x /sbin/chkconfig ] ; then

	echo "# chkconfig: 2345 60 40" >> /etc/init.d/tomcat-enstratus
	echo "# description: Manages the enStratus agent." >> /etc/init.d/tomcat-enstratus
	cat /enstratus/bin/tomcat-enstratus >> /etc/init.d/tomcat-enstratus
	
	echo "# chkconfig: 2345 60 40" >> /etc/init.d/enstratus
	echo "# description: Manages the enStratus agent." >> /etc/init.d/enstratus
	cat /enstratus/bin/enstratus >> /etc/init.d/enstratus
	
	chmod 755 /etc/init.d/tomcat-enstratus
	chmod 755 /etc/init.d/enstratus
	
	chkconfig --add tomcat-enstratus	
	chkconfig --add enstratus	
	
else
	echo "Could not identify startup protocols. Contact enStratus support at support@enstratus.com."
	exit 90
fi
echo "Done."

echo "Starting enStratus Tomcat process on port 2003..."
/etc/init.d/tomcat-enstratus start &
echo "Done."

chown enstratus:enstratus /mnt/tmp
