#!/bin/bash

# Copyright 2010 enStratus Networks LLC
#
# install - Installs enStratus on a UNIX system
# 
# This software is part of the enStratus Cloud Management System. Only 
# authorized licensees of enStratus may use this software and only
# in the context of enStratus-managed virtual servers and machine images. 
# Unauthorized copying or distribution of this software is strictly prohibited.
# Authorized licensees may copy this software onto any machine images
# and/or virtual hosts being managed by the enStratus system as needed.
#
# FUNCTION
# Call this script to install enStratus on a UNIX system.

if [ -z "$JAVA_HOME" ] ; then
    JAVA_HOME="/opt/local/java/sun6/"
fi

set -u

CMD=${0}
BASEDIR=`dirname ${CMD}`
INSTALL=`basename ${CMD}`

if [ $# -lt 1 ] ; then
    echo "Syntax: install.sh [Amazon|Atmos|ATT|Azure|Bluelock|CloudCentral|CloudSigma|CloudStack|Eucalyptus|GoGrid|Google|Joyent|OpenStack|Rackspace|ServerExpress|Terremark|VMware] [production|staging] [provisioningProxyIP:port]"
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
    echo "Syntax: install.sh [Amazon|Rackspace|ReliaCloud|Terremark|Azure|Eucalyptus|CloudStack|GoGrid|Google|CloudCentral|OpenStack] [production|staging|testing|development] [provisioningProxyIP:port]"
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

/usr/bin/perl -v > /dev/null 2>&1

if [ $? != 0 ] ; then
	echo "Perl must be installed on this system in order for enStratus to run."
	exit 12
fi

echo "Creating enstratus directory at /opt/local/enstratus..."
if [ ! -d /opt/local/enstratus ] ; then
	/bin/mkdir /opt/local/enstratus
	if [ $? != 0 ] ; then
		echo "Could not create /opt/local/enstratus directory. Are you running this as root?"
		exit 30
	fi
fi
echo "Done."

echo "Creating services directory at /var/enstratus..."
if [ ! -d /var/enstratus ] ; then
	/bin/mkdir /var/enstratus
	if [ $? != 0 ] ; then
		echo "Could not create /var/enstratus directory. Are you running this as root?"
		exit 30
	fi
	/bin/mkdir /var/enstratus/tmp
fi
echo "Done."

echo "Creating enstratus user and group..."
id enstratus 2> /dev/null
if [ $? != 0 ] ; then
	/usr/sbin/groupadd enstratus 2> /dev/null
	if [ $? != 0 ] ; then
		echo "Failed to add enstratus group."
		exit 40
	fi
	#
	# Account needs a password for sudo rights, so we assign it one
	# Remote access via password should be disabled in cloud
	#
	/usr/sbin/useradd -d /opt/local/enstratus/home -g enstratus -s /bin/bash -m enstratus 2> /dev/null
	if [ $? != 0 ] ; then
		echo "Failed to add enstratus user. Please add an enstratus user manually and restart the script."
		echo "The script will take over gracefully when you restart it."
		exit 41
	fi
fi
echo "Done."

echo "Setting enstratus permissions..."
/bin/chown enstratus:enstratus /opt/local/enstratus
/bin/chmod 775 /opt/local/enstratus
/bin/chown -R enstratus:enstratus /var/enstratus
/bin/chmod 775 /var/enstratus
echo "Done."

echo "Installing enStratus into /opt/local/enstratus..."
cp -R ${BASEDIR}/* /opt/local/enstratus
rm -f /opt/local/enstratus/${INSTALL}
rm -f /opt/local/enstratus/upgrade.sh

sudo sed "s|javaHome|$JAVA_HOME|g" /opt/local/enstratus/bin/enstratus-service > /var/tmp/enstratus-service
sudo mv /var/tmp/enstratus-service /opt/local/enstratus/bin/enstratus-service

echo "cloud=${CLOUD}" > /opt/local/enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg
echo "environment=${ESENV}" >> /opt/local/enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg
echo "$PROXY" >> /opt/local/enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg

/bin/chown -R enstratus:enstratus /opt/local/enstratus
/bin/chmod 750 /opt/local/enstratus/bin
/bin/chmod 550 /opt/local/enstratus/bin/*
/bin/chmod 755 /opt/local/enstratus/custom/bin
/bin/chmod -R 750 /opt/local/enstratus/home
/bin/chmod 750 /opt/local/enstratus/cfg
/bin/chmod 640 /opt/local/enstratus/cfg/*
/bin/chmod 754 /opt/local/enstratus/ws/tomcat/bin/*.sh
echo "Done.";

echo "Adding enStratus user to /etc/sudoers..."
/bin/chmod u+w /opt/local/etc/sudoers
echo "%enstratus    ALL=(ALL) NOPASSWD: ALL" | tee -a /opt/local/etc/sudoers
/usr/bin/perl -ni -e 'print unless /requiretty/' /opt/local/etc/sudoers
/bin/chmod u-w /opt/local/etc/sudoers
echo "Done."

#echo "Attempting to install startup scripts..."
#
####  Insert SMF Stuff Here  #####
#
#echo "Done."

#echo "Starting enStratus Tomcat process on port 2003..."
#/etc/init.d/tomcat-enstratus start &
#echo "Done."
