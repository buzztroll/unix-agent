#!/usr/bin/env bash
# DCM Agent Installer for Linux

SHELL_PID=$$

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

# Install agent. It downloads a distro-specific agent.
function install_agent(){
	case $platform in
		"ubuntu")
			url='http://es-download.s3.amazonaws.com/dcm-agent-latest.deb'
			filename='dcm-agent.deb'
			CHMOD_CMD=chmod
			CHOWN_CMD=chown
			;;
		"el" | "suse")
			url='http://es-download.s3.amazonaws.com/dcm-agent-latest.rpm'
			filename='dcm-agent.rpm'
			CHMOD_CMD=/bin/chmod
			CHOWN_CMD=/bin/chown
			;;
		* )
			echo "[ERROR] not supported OS. platform: ${platform}" >&2
			exit 1
	esac

	echo "Downloading DCM Agent from $url"
	echo "This may take a few minutes."

        if [ "X$AGENT_LOCAL_PACKAGE" == "X" ]; then
		curl -s -L $url > /tmp/$filename
        else
		cp $AGENT_LOCAL_PACKAGE /tmp/$filename
        fi

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

	echo "Installing DCM Agent."
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

# Detect an existing agent and kill it.

# Install agent.
install_agent

# Create configuration file.
/opt/dcm-agent/embedded/bin/dcm-agent-configure -i --base-path /dcm

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
