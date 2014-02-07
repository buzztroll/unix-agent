#!/bin/bash

set -u

apt-get update
apt-get upgrade -y
dpkg-reconfigure tzdata

for pkg in {zip,unzip,less,secure-delete,vim,postfix,build-essential};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
		echo "ERROR: ${pkg} did not install!"
		exit 127
	fi
done

for pkg in {mysql-server,python-mysqldb,python-json};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
		echo "ERROR: ${pkg} did not install!"
		exit 127
	fi
done

for pkg in {mdadm,xfsprogs,sun-java6-jdk,cryptsetup};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
		echo "ERROR: ${pkg} did not install!"
		exit 127
	fi
done


apt-get install -y ec2-ami-tools

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

for pkg in {tomcat5.5,sysstat,apache2,libapache2-mod-jk,haproxy,cronolog};
do
	apt-get -qq install -y ${pkg}
	if [ $? != 0 ]; then
		echo "ERROR: ${pkg} did not install!"
		exit 127
	fi
done

#moving haproxy config for startProxy script
sudo mv /etc/haproxy/haproxy.cfg /etc/

# Default bastille install. Please modify to suit your needs.
#bastille config

sudo cat > /etc/Bastille/config << EOM

# enStratus automated Bastille Confiuration
# Q:  Would you like to enforce password aging? [Y]
AccountSecurity.passwdage="N"
# Q:  Should Bastille disable clear-text r-protocols that use IP-based authentication? [Y]
AccountSecurity.protectrhost="Y"
# Q:  Should we disallow root login on tty's 1-6? [N]
AccountSecurity.rootttylogins="Y"
# Q:  Would you like to deactivate the Apache web server? [Y]
Apache.apacheoff="N"
# Q:  Would you like to bind the Web server to listen only to the localhost? [N]
Apache.bindapachelocal="N"
# Q:  Would you like to bind the web server to a particular interface? [N]
Apache.bindapachenic="N"
# Q:  Would you like to password protect single-user mode? [Y]
BootSecurity.passsum="Y"
# Q:  Should we restrict console access to a small group of user accounts? [N]
ConfigureMiscPAM.consolelogin="N"
# Q:  Would you like to put limits on system resource usage? [N]
ConfigureMiscPAM.limitsconf="N"
# Q:  Would you like to set more restrictive permissions on the administration utilities? [N]
FilePermissions.generalperms_1_1="Y"
# Q:  Would you like to disable SUID status for mount/umount?
FilePermissions.suidmount="Y"
# Q:  Would you like to disable SUID status for ping? [Y]
FilePermissions.suidping="Y"
# Q:  Would you like to disable SUID status for traceroute? [Y]
FilePermissions.suidtrace="Y"
# Q:  Would you like to run the packet filtering script? [N]
Firewall.ip_intro="N"
# Q:  Would you like to add additional logging? [Y]
Logging.morelogging="Y"
# Q:  Would you like to set up process accounting? [N]
Logging.pacct="N"
# Q:  Do you have a remote logging host? [N]
Logging.remotelog="N"
# Q:  Would you like to deactivate NFS and Samba? [Y]
MiscellaneousDaemons.remotefs="Y"
# Q:  Would you like to disable printing? [N]
Printing.printing="Y"
# Q:  Would you like to disable printing? [N]
Printing.printing_cups="Y"
# Q:  Would you like to display "Authorized Use" messages at log-in time? [Y]
SecureInetd.banners="Y"
# Q:  Should Bastille ensure inetd's FTP service does not run on this system? [y]
SecureInetd.deactivate_ftp="Y"
# Q:  Should Bastille ensure the telnet service does not run on this system? [y]
SecureInetd.deactivate_telnet="Y"
# Q:  Who is responsible for granting authorization to use this machine?
SecureInetd.owner="enStratus Networks LLC"
# Q:  Would you like to set a default-deny on TCP Wrappers and xinetd? [N]
SecureInetd.tcpd_default_deny="N"
# Q:  Do you want to stop sendmail from running in daemon mode? [Y]
Sendmail.sendmaildaemon="N"
# Q:  Would you like to install TMPDIR/TMP scripts? [N]
TMPDIR.tmpdir="N"

EOM

# Now install Bastille and run in batch mode.
# Need a little trick for Debian/Lenny
mv /etc/debian_version /etc/debian_version.bak
echo "4.0 "> /etc/debian_version
apt-get -y install bastille
bastille -b
mv /etc/debian_version.bak /etc/debian_version

#64-bit instances only:
#ln -s /usr/lib/jvm/java-1.5.0-sun/jre/lib/amd64/libmlib_image.so /usr/lib

/etc/init.d/mysql stop
rm /etc/init.d/mysql
update-rc.d mysql remove

/etc/init.d/mysql-ndb stop
rm /etc/init.d/mysql-ndb
update-rc.d mysql-ndb remove

/etc/init.d/mysql-ndb-mgm stop
rm /etc/init.d/mysql-ndb-mgm
update-rc.d mysql-ndb-mgm remove

/etc/init.d/tomcat5.5 stop
rm /etc/init.d/tomcat5.5
update-rc.d tomcat5.5 remove

# Debian, remove avahi
/etc/init.d/avahi-daemon stop
rm /etc/init.d/avahi-daemon
update-rc.d avahi-daemon remove

#disable apache
/etc/init.d/apache2 stop
sudo update-rc.d -f apache2 remove

mv /etc/debian_version.bak /etc/debian_version
#add permissions back, because bastille wipes them out
sudo chmod 755 /usr/bin/ssh
sudo chmod 755 /usr/bin/scp

wget http://www.ossec.net/files/ossec-hids-2.2.tar.gz
tar -xzf ossec-hids-2.2.tar.gz
cd ossec-hids-2.2
./install.sh

usermod --groups ossec enstratus
 
