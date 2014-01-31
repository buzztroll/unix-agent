#!/usr/bin/env bash
# Enstratius Agent Installer for Linux
# maintainer: sean.kang@enstratius.com

SHELL_PID=$$

# Default values for arguments.
DEFAULT_CLOUD='Amazon'
DEFAULT_ENVIRONMENT='production'
DEFAULT_PROXY='provisioning.enstratus.com:3302'
DEFAULT_META_DATA='none'
DEFAULT_USER_DATA='none'
DEFAULT_HANDSHAKE_RETRY_MINUTES='none'

# Show help messages.
function show_help(){
	echo "============================================================================================"
	echo "Enstratius Agent Installer for linux."
	echo "Usage: http://es-download.s3.amazonaws.com/install.sh | bash -s - [OPTIONS] ..."
	echo
	echo " -c <cloud provider>,     set cloud provider"
	echo "------------------------------------ List of supported clouds ------------------------------"
	echo "Amazon, Atmos, ATT, Azure, Bluelock, CloudCentral, CloudSigma, CloudStack, CloudStack3"
	echo "Eucalyptus, GoGrid, Google, IBM, Joyent, OpenStack, Rackspace, ServerExpress, Terremark"
	echo "VMware, Other"
	echo "--------------------------------------------------------------------------------------------"
	echo " -p <address>,            set provisioning server IP address and port"
	echo " -e <production|staging>, set type of environment"
	echo " -m <metadata>,           set metadata"
	echo " -u <userdata>,           set userdata"
	echo " -t <minutes>,            set handshake retry minutes"
	echo " -j <JAVA_HOME>,          set JAVA_HOME manually"
	echo " -C,                      install chef-client after the installation of agent"
	echo " -d,                      install debug agent. This is only for test."
	echo " -h,                      display this help and exit"
	echo
	echo "Example:"
	echo "curl http://es-download.s3.amazonaws.com/install.sh | bash -s - -c Amazon"
	echo "curl http://es-download.s3.amazonaws.com/install.sh | bash -s - -c IBM -p 1.2.3.4:3302"
	echo "============================================================================================"
}

# Read input from terminal even if stdin is pipe.
# This function is to be used for interactive dialogue.
function read_terminal() {
	local input
	if [ -t 0 ]; then
		read input
	else
		local input_terminal=/dev/$(ps | awk '$1=='$SHELL_PID' {print $2}')
		local temp_fd_num=10
		while [ -e /dev/fd/${temp_fd_num} ]; do
			temp_fd_num=$((temp_fd_num+1))
		done
		eval "exec $temp_fd_num< $input_terminal"
		eval "read -u$temp_fd_num input"
		eval "exec $temp_fd_num<&-"
	fi
	echo $input
}

# Detect an existing agent and kill it.
function detect_running_agent(){
	agent=$( ps -ef | grep '[Tt]omcat' | grep enstratus | awk '{print $2}' | wc -l )

	if [ $agent -gt 0 ]; then
		echo "Found a running agent. Unceremoniously killing it and cleaning up logs."
		rm -f /enstratus/ws/tomcat/logs/*
		agent_pid=$( ps -ef | grep '[Tt]omcat' | grep enstratus | awk '{print $2}' )
		kill -9 $agent_pid
	fi
}

# Install agent. It downloads a distro-specific agent.
function install_agent(){
	case $platform in
		"ubuntu")
			url='http://es-download.s3.amazonaws.com/enstratius-agent-latest.deb'
			[[ $install_debug_agent == "yes" ]] && url='http://es-download.s3.amazonaws.com/enstratius-agent-debug-latest.deb'
			filename='enstratius-agent.deb'
			CHMOD_CMD=chmod
			CHOWN_CMD=chown
			;;
		"el" | "suse")
			url='http://es-download.s3.amazonaws.com/enstratius-agent-latest.rpm'
			[[ $install_debug_agent == "yes" ]] && url='http://es-download.s3.amazonaws.com/enstratius-agent-debug-latest.rpm'
			filename='enstratius-agent.rpm'
			CHMOD_CMD=/bin/chmod
			CHOWN_CMD=/bin/chown
			;;
		* )
			echo "[ERROR] not supported OS. platform: ${platform}" >&2
			exit 1
	esac

	echo "Downloading Enstratius Agent from $url"
	echo "This may take a few minutes."

	curl -s -L $url > /tmp/$filename 

	if [ $? -ne 0 ]; then
		echo "[ERROR] Download failed. Cannot install the agent."
		exit 1
	fi

	if [ ! -s /tmp/$filename ]; then
		echo "[ERROR] Unable to retrieve a valid package!"
		report_bug
		echo "URL: $url"
		exit 1
	fi
   
	echo "Installing Enstratius Agent."
	cd /tmp

	case $platform in
		ubuntu )
			dpkg -i $filename;;
		el | suse )
			rpm -Uvh $filename;;
	esac
	if [ $? -ne 0 ]; then
		echo "[ERROR] Installation failed."
		report_bug
		exit 1
	fi

	cd ~
	rm -f /tmp/${filename} 2>&1 > /dev/null
	rm -rf /tmp/enstratus 2>&1 > /dev/null
}

function ask_install(){
	local program=$1
	local answer

	while true; do
		echo -n "Do you want to install ${program} by using system's package manager? (Y/N) "
		answer=$( read_terminal | tr '[:lower:]' '[:upper:]' )
		case $answer in
			Y|YES) 
				return 1
				;;
			N|NO)
				return 0
				;;
		esac
	done
}

function make_config() {
	local CLOUD=$1
	local ESENV=$2
	local PROXY=$3
	local META_DATA=$4
	local USER_DATA=$5
	local HANDSHAKE_RETRY_MINUTES=$6
	local CONFIG_FILE=/enstratus/ws/content/WEB-INF/classes/enstratus-webservices.cfg

	echo "cloud=${CLOUD}" > ${CONFIG_FILE}
	echo "environment=${ESENV}" >> ${CONFIG_FILE}
	echo "provisioningProxy=${PROXY}" >> ${CONFIG_FILE}
	[[ $META_DATA != "none" ]] && echo "metaData=${META_DATA}" >> ${CONFIG_FILE}
	[[ $USER_DATA != "none" ]] && echo "userData=${USER_DATA}" >> ${CONFIG_FILE}
	[[ $HANDSHAKE_RETRY_MINUTES != "none" ]] && echo "handshakeRetryMinutes=${HANDSHAKE_RETRY_MINUTES}" >> ${CONFIG_FILE}
	$CHOWN_CMD -R enstratus:enstratus $CONFIG_FILE
}

# Print bug report information.
function report_bug() {
	echo
	echo "Please file a bug report at http://support.enstratius.com"
	echo "Project: Enstratius Agent"
	echo "Component: Packages"
	echo
	echo "Please detail your operating system type, version and any other relevant details. Thank you."
}

# Test javac using JAVA_HOME. If javac is not executable, installer will quit.
function test_java(){
	local JAVA_HOME=$1
	local platform=$2

	local javaTest="${JAVA_HOME}/bin/javac"

	if [ ! -x "$javaTest" ] ; then
	  	echo "[ERROR] You must install a valid JDK and point JAVA_HOME to that JDK."
	  	echo "[ERROR] The JDK must include javac."
		report_bug
		exit 1
	else
		export JAVA_HOME=$JAVA_HOME
	fi
}

function install_java(){
	local platform=$1
	echo "Installing JDK for ${platform}."
	case $platform in
		"ubuntu")
			apt-get update 2>&1 > /dev/null
			apt-get -q -y install openjdk-6-jdk 2>&1 > /dev/null
			if [ $? != 0 ]; then
				echo "[ERROR] Could not install java for ${platform}."
				exit 100
			else
				echo "Done."
				JAVA_HOME=$(readlink -f `which javac` | sed 's:/bin/java[c]::')
			fi
			;;
		"el")
			yum -y install java-1.6.0-openjdk-devel 2>&1 > /dev/null
			if [ $? != 0 ]; then
				echo "[ERROR] Could not install java for ${platform}."
				exit 100
			else
				echo "Done."
				JAVA_HOME=$(readlink -f `which javac` | sed 's:/bin/java[c]::')
			fi
			;;
		"suse" )
			zypper -n install java-1_6_0-ibm-devel 2>&1 > /dev/null
			if [ $? != 0 ]; then
				echo "[ERROR] Could not install java for ${platform}."
				exit 100
			else
				echo "Done."
				JAVA_HOME=$(readlink -f `which javac` | sed 's:/bin/java[c]::')
			fi
			;;
		* )
			echo "Please install JDK manually."
			exit 1
			;;
	esac
}

# Search JDK and set JAVA_HOME
function search_for_java(){
	local platform=$1

	local OPEN_JDK_DIRS="/usr/lib/jvm/java-1.6.0-openjdk.x86_64 /usr/lib/jvm/jre-1.6.0-openjdk.x86_64 /usr/lib/jvm/java-6-openjdk-amd64 /usr/lib/jvm/java-1.6.0-openjdk" 
	local ORACLE_JDK_DIRS="/usr/lib/jvm/java-6-sun /usr/lib/jvm/java-1.5.0-sun /usr/lib/j2sdk1.5-sun /usr/lib/j2sdk1.4-sun /usr/lib/j2sdk1.3-sun "
	local IBM_JDK_DIRS="/usr/lib/j2sdk1.5-ibm /usr/lib/j2sdk1.4-ibm /usr/lib64/jvm/java-1.6.0-ibm /usr/lib/jvm/java-1.6.0-ibm"
	local SOME_DIRS="/usr/java/jdk1.6.0_02 /usr/lib/j2sdk1.4-blackdown /usr/lib/j2se/1.4 /usr/lib/j2sdk1.3-blackdown /usr/lib/jvm/java-gcj /usr/lib/kaffe "
	local OTHER_DIRS=$( echo /usr/java/jdk1.{6,7}.0_{13..64} )
	local JDK_DIRS=$OPEN_JDK_DIRS" "$ORACLE_JDK_DIRS" "$IBM_JDK_DIRS" "$SOME_DIRS" "$OTHER_DIRS
  
	for jdir in ${JDK_DIRS}; do
		if [ -r "${jdir}/bin/javac" -a -z "${JAVA_HOME}" ]; then
			JAVA_HOME_TMP="${jdir}"
			if [ -r "${jdir}/bin/jdb" ]; then
				JAVA_HOME="${JAVA_HOME_TMP}"
			fi
		fi
	done

	export JAVA_HOME=${JAVA_HOME}
}

# Interactive dialogue to get arguments from terminal.
function get_options_from_dialogue() {
	echo "-----------------------------------------------------------------------------------------------"
	echo " 1) Amazon      2) Atmos       3) ATT          4) Azure       5) Bluelock       6) CloudCentral"
	echo " 7) CloudSigma  8) CloudStack  9) CloudStack3 10) Eucalyptus 11) GoGrid        12) Google"
	echo "13) IBM        14) Joyent     15) OpenStack   16) Rackspace  17) ServerExpress 18) Terremark"
	echo "19) VMware     20) Other"
	echo "-----------------------------------------------------------------------------------------------"

	while [[ -z $cloud || $cloud == "wrong" ]]; do
		echo -n "What cloud is this server hosted in? [1-20] (Default: Amazon) "
		input=$(read_terminal)
		case $input in
			1) cloud=Amazon;;
			2) cloud=Atmos;;
			3) cloud=ATT;;
			4) cloud=Azure;;
			5) cloud=Bluelock;;
			6) cloud=CloudCentral;;
			7) cloud=CloudSigma;;
			8) cloud=CloudStack;;
			9) cloud=CloudStack3;;
			10) cloud=Eucalyptus;;
			11) cloud=GoGrid;;
			12) cloud=Google;;
			13) cloud=IBM;;
			14) cloud=Joyent;;
			15) cloud=OpenStack;;
			16) cloud=Rackspace;;
			17) cloud=ServerExpress;;
			18) cloud=Terremark;;
			19) cloud=VMware;;
			20) cloud=Other;;
			"") cloud=$DEFAULT_CLOUD;;
			*)  cloud=wrong;;
		esac
	done;

	echo -n "What is the Agent Endpoint this agent should communicate with? (Default: provisioning.enstratus.com:3302) "
	proxy=$(read_terminal)

	# If proxy is default value, production will be set.
	if [[ $proxy == "" || $proxy == $DEFAULT_PROXY ]]; then
		environment=production
	fi

	while [[ -z $environment || $environment == "wrong" ]]; do
		echo -n "Does the Agent Endpoint have an SSL Certificate signed by a known public issuer? (Y/N) "
		environment_answer=$( read_terminal | tr '[:upper:]' '[:lower:]' )
		case $environment_answer in
			y | yes )
				environment=production;;
			n | no )
				environment=staging;;
			*)
				environment=wrong;;
		esac
	done

	case $cloud in
		CloudStack)
			meta_data="lastest/instance-id"
			;;
		CloudStack3)
			while [[ -z $cloudstack_answer || $cloudstack_answer == "wrong" ]]; do
				echo -n "Are you using CloudStack 3.0.4? (Y/N) "
				cloudstack_answer=$( read_terminal | tr '[:upper:]' '[:lower:]' )
				case $cloudstack_answer in
					y | yes)
						meta_data="latest/local-hostname"
						handshake_retry_minutes=60
						;;
					n | no)
						meta_data="latest/vm-id"
						;;
					*)
						cloudstack_answer=wrong
						;;
				esac
			done
			;;
		Eucalyptus)
			echo -n "What would you set user_data? (Default: http://169.254.169.254/1.0/meta-data) "
			user_data=$(read_terminal)
			[ -z $user_data ] && user_data="http://169.254.169.254/1.0/meta-data"
			;;
	esac
}

# Install chef-client.
function install_chef_client {
	while [[ $chef_install != "yes" && $cmd_opts_install != "yes" ]]; do
		echo -n "(Optional) Would you like to install chef client? (Y/N) "
		chef_install=$( read_terminal | tr '[:upper:]' '[:lower:]' )
		case $chef_install in
			y | yes)
				chef_install="yes"
				break;;
			n | no)
				chef_install="no"
				break;;
			*)
				chef_install="wrong";;
		esac
	done

	if [[ $chef_install == "yes" ]]; then
		echo "Installing chef-client."
		curl -L https://www.opscode.com/chef/install.sh | bash
		echo "Done."
	fi
}

# Install dependent packages.
function install_dependent_packages {
	echo "Installing dependent packages. This may take a few mintues."
	case $platform in
		ubuntu )
			apt-get update 2>&1 > /dev/null
			DEBIAN_FRONTEND=noninteractive apt-get -qq -y install secure-delete xfsprogs xfslibs-dev xfsdump mdadm openssl cryptsetup zip unzip sysstat
			;;
		el )
			yum -y install xfsprogs cryptsetup tar bzip2 gzip zip unzip rsync mdadm sysstat
			;;
		suse )
			zypper -n install xfsprogs cryptsetup tar bzip2 gzip zip unzip rsync mdadm sysstat
			;;
	esac
	echo "Done."
}

# Check the arguments and decide if interactive dialogue starts.
if [ $# == 0 ]; then
	show_help
	while [[ $diag_answer == "wrong" || -z $diag_answer ]]; do
		echo -n "Would you like to start interactive dialogue to configure arguments? (Y/N) "
		diag_answer=$( read_terminal | tr '[:upper:]' '[:lower:]' )
		case $diag_answer in
			y | yes)
				cmd_opts_install="no"
				get_options_from_dialogue
				;;
			n | no)
				exit 1;;
			*)
				diag_answer=wrong;;	
		esac
	done
else
	cmd_opts_install="yes"
	while getopts j:c:p:e:m:u:t:CdDh opt; do
		case "$opt" in
			j) JAVA_HOME="$OPTARG";;
			c) cloud="$OPTARG";;
			p) proxy="$OPTARG";;
			e) environment="$OPTARG";;
			m) meta_data="$OPTARG";;
			u) user_data="$OPTARG";;
			t) handshake_retry_minutes="$OPTARG";;
			C) chef_install="yes";;
			d) install_debug_agent="yes";;
			D) ;; # deprecated. dependent packages will be installed all the time.
			h) show_help
			   exit 1;;
		esac
	done
fi

shift $((OPTIND-1))

# Identify platform.
if [ -x "/usr/bin/lsb_release" ]; then
	lsb_info=$(/usr/bin/lsb_release -i | cut -f2)
	case $lsb_info in
		"Ubuntu") platform="ubuntu";;
		"CentOS") platform="el";;
		"RedHatEnterpriseServer") platform="el";;
		"SUSE LINUX") platform="suse";;
		"n/a") platform="el";;
	esac
elif [ -f "/etc/redhat-release" ]; then
	redhat_info=$(cat /etc/redhat-release | awk '{print $1}')
	case $redhat_info in
		CentOS) platform="el";;
		Red) platform="el";;
	esac
elif [ -f "/etc/debian_version" ]; then
	platform="debian"
elif [ -f "/etc/SuSE-release" ]; then
	platform="suse"
elif [ -f "/etc/system-release" ]; then
	platform=$(sed 's/^\(.\+\) release.\+/\1/' /etc/system-release | tr '[A-Z]' '[a-z]')
	# amazon is built off of fedora, so act like RHEL
	if [ "$platform" = "amazon linux ami" ]; then
		platform="el"
	fi
else
	echo "[ERROR] Unable to identify platform."
	exit 1
fi

echo "Starting the installation process..."

# Find JDK and install it if there's no existing one.
if [ -z $JAVA_HOME ]; then
	search_for_java $platform
	if [ -z $JAVA_HOME ] ; then
		echo "Could not find Java."
		install_java $platform
	fi
fi

# Test if JDK works properly.
test_java $JAVA_HOME $platform

# Set default value of arguments.
[[ -z $cloud ]] && cloud=$DEFAULT_CLOUD
[[ -z $proxy ]] && proxy=$DEFAULT_PROXY
[[ -z $environment ]] && environment=$DEFAULT_ENVIRONMENT
[[ -z $meta_data ]] && meta_data=$DEFAULT_META_DATA
[[ -z $user_data ]] && user_data=$DEFAULT_USER_DATA
[[ -z $handshake_retry_minutes ]] && handshake_retry_minutes=$DEFAULT_HANDSHAKE_RETRY_MINUTES

# Detect an existing agent and kill it.
detect_running_agent

# Install dependent packages.
install_dependent_packages

# Install agent.
install_agent

# Create configuration file.
make_config $cloud $environment $proxy $meta_data $user_data $handshake_retry_minutes

# Notification for non-native packages.
if [[ $platform != 'ubuntu' ]]; then
	echo "========================================================================================="
	echo "[ALERT] secure-delete was not installed since it is not natively available in ${platform}."
	echo "[ALERT] If you want to make secure-delete functional, please download and install it."
	echo "[ALERT] http://sourceforge.net/projects/srm/"
	echo "========================================================================================="
fi

# Install optional packages.
install_chef_client
