#!/usr/bin/env bash


if [ -z "$JAVA_HOME" ] ; then
    JAVA_HOME=""
fi

set -u

exec_dir=$(readlink -f $(dirname $0))

doneUpgrade() {
	if [ ! -d /enstratus ] ; then
		sudo mv /enstratus.bak /enstratus
	fi
	sudo /etc/init.d/tomcat-enstratus start
	exit 0
}

# Trying to delete any previous backups.
sudo rm -rf /enstratus.bak

sleep 10

# Stopping any running enStratus instances.
sudo /etc/init.d/tomcat-enstratus stop &> /dev/null

sleep 10

# Create a new backup.
sudo mv /enstratus /enstratus.bak

trap doneUpgrade INT TERM EXIT

#This will happen during the install

if [ ! -d /enstratus ] ; then
	sudo mkdir /enstratus
	if [ $? != 0 ] ; then
		echo "Could not create /enstratus directory."
		exit 30
	fi
fi

# This will happen during the install
sudo chown enstratus:enstratus /enstratus
sudo chmod 775 /enstratus

sudo cp -R $exec_dir/* /enstratus
sudo rm -f /enstratus/install.sh
sudo rm -f /enstratus/upgrade.sh

if [ -r /enstratus.bak/bin/enstratus-service ] ; then
	sudo rm -f /enstratus/bin/enstratus-service
	sudo cp /enstratus.bak/bin/enstratus-service /enstratus/bin
else

	SOME_DIRS="/usr/lib/jvm/java-1.6.0-openjdk /usr/lib/jvm/java-6-sun /usr/java/jdk1.6.0_02 /usr/lib/jvm/java-1.5.0-sun /usr/lib/j2sdk1.5-sun /usr/lib/j2sdk1.5-ibm /usr/lib/j2sdk1.4-sun /usr/lib/j2sdk1.4-blackdown /usr/lib/j2se/1.4 /usr/lib/j2sdk1.4-ibm /usr/lib/j2sdk1.3-sun /usr/lib/j2sdk1.3-blackdown /usr/lib/jvm/java-gcj /usr/lib/kaffe"

	OTHER_DIRS=$( echo /usr/java/jdk1.6.0_{13..21} )

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
	if [ -f /mnt/tmp/enstratus-service.bak ] ; then
		sudo rm /mnt/tmp/enstratus-service.bak
	fi
	sudo sed "s|javaHome|$JAVA_HOME|g" /enstratus/bin/enstratus-service > /mnt/tmp/enstratus-service
	sudo mv /mnt/tmp/enstratus-service /enstratus/bin/enstratus-service
fi

sudo chmod 750 /etc/init.d/tomcat-enstratus
sudo mv /enstratus/bin/tomcat-enstratus /etc/init.d/tomcat-enstratus
sudo chmod 755 /etc/init.d/tomcat-enstratus

sudo chmod 750 /etc/init.d/enstratus
sudo mv /enstratus/bin/enstratus /etc/init.d/enstratus
sudo chmod 755 /etc/init.d/enstratus

sudo chown -R enstratus:enstratus /enstratus

sudo chmod 750 /enstratus/bin
sudo chmod 550 /enstratus/bin/*
sudo chmod 755 /enstratus/custom/bin
sudo chmod 750 /enstratus/ws/tomcat/bin/*.sh
if [ -d /enstratus.bak/home/.ssh ] ; then
    sudo mv /enstratus.bak/home/.ssh /enstratus/home/.ssh
fi
if [ -f /enstratus.bak/ws/content/WEB-INF/classes/enstratus-webservices.cfg ] ; then
    sudo cp /enstratus.bak/ws/content/WEB-INF/classes/enstratus-webservices.cfg /enstratus/ws/content/WEB-INF/classes
fi
sudo cp -r /enstratus.bak/custom/* /enstratus/custom/ &> /dev/null
sudo chmod 750 /enstratus/cfg
sudo chmod 640 /enstratus/cfg/*
chown enstratus:enstratus /mnt/tmp/


echo "enStratus Agent upgraded"
echo ""
echo "Using the following configuration, please verify :"
echo -e "JAVA_HOME=$(sed -rn "s/.*JAVA_HOME=(.*)$/\1/p" /enstratus/bin/enstratus-service)"
echo -e "cloud=$(egrep "^cloud=" /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg | cut -f 2 -d '=')"
echo -e "environment=$(egrep "^environment=" /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg | cut -f 2 -d '=')"
echo -e "provisioningProxy=$(egrep "^provisioningProxy=" /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg | cut -f 2 -d '=')"
echo -e "metaData(optional)=$(egrep "^metaData=" /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg | cut -f 2 -d '=')"
echo -e "userData(optional)=$(egrep "^userData=" /enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg | cut -f 2 -d '=')"
echo ""
echo "Agent will be restarted:"
echo ""


