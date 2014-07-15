#!/usr/bin/env bash
# DCM Agent Installer for Linux

SHELL_PID=$$
installer_cmd=""

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
    base_url=$1
    filename=$2
    url="$base_url/$filename"
    echo "Downloading DCM Agent from $url"
    echo "This may take a few minutes."

    if [ "X$AGENT_LOCAL_PACKAGE" == "X" ]; then
        curl -L $url > /tmp/$filename
    else
        cp $AGENT_LOCAL_PACKAGE /tmp/$filename
    fi

    if [ $? -ne 0 ]; then
        echo "[ERROR] Download failed. Cannot install the agent."
        echo "$url was not found."
        echo "Your distribution may not be supported."
        exit 1
    fi

    if [ ! -s /tmp/$filename ]; then
        echo "[ERROR] Unable to retrieve a valid package!"
        echo "URL: $url"
        exit 1
    fi

    echo "Installing DCM Agent."
    cd /tmp

    $installer_cmd $filename
    if [ $? -ne 0 ]; then
        echo "[ERROR] Installation failed."
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
    distro_version=$(/usr/bin/lsb_release -r | cut -f2)
    case $lsb_info in
        "Ubuntu")
            platform="ubuntu"
            distro_name="ubuntu"
            pkg_ext="deb"
            installer_cmd="dpkg -i"
            ;;
        "Debian")
            platform="debian"
            distro_name="debian"
            pkg_ext="deb"
            installer_cmd="dpkg -i"
            ;;
        "CentOS")
            platform="el"
            distro_name="centos"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
            ;;
        "RedHatEnterpriseServer")
            platform="el"
            distro_name="rhel"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
            ;;
        "SUSE LINUX")
            platform="suse"
            distro_name="suse"
            pkg_ext="deb"
            installer_cmd="dpkg -i"
            ;;
        "n/a")
            echo "Sorry we could not detect your environment"
            exit 1
            ;;
    esac
elif [ -f "/etc/redhat-release" ]; then
    redhat_info=$(cat /etc/redhat-release)
    distro=$(echo $redhat_info | awk '{print $1}')
    case $distro in
        CentOS)
            platform="el"
            distro_version=$(echo $redhat_info | awk '{print $3}')
            distro_name="centos"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
        ;;
        Red)
            platform="el"
            distro_version=$(echo $redhat_info | awk '{print $4}')
            distro_name="rhel"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
        ;;
    esac
elif [ -f "/etc/debian_version" ]; then
    platform="debian"
    distro_version=$(cat /etc/debian_version)
    distro_name="debian"
    pkg_ext="deb"
    installer_cmd="dpkg -i"
elif [ -f "/etc/SuSE-release" ]; then
    distro_version=$(cat /etc/issue | awk '{print $2}')
    distro_name="suse"
    platform="suse"
    pkg_ext="deb"
    installer_cmd="dpkg -i"
elif [ -f "/etc/system-release" ]; then
    platform=$(sed 's/^\(.\+\) release.\+/\1/' /etc/system-release | tr '[A-Z]' '[a-z]')
    # amazon is built off of fedora, so act like RHEL
    if [ "$platform" = "amazon linux ami" ]; then
        platform="el"
        pkg_ext="rpm"
        installer_cmd="rpm -Uvh"
    fi
else
    echo "[ERROR] Unable to identify platform."
    exit 1
fi

distro_version=`echo $distro_version | awk -F '.' '{ print $1 "." $2 }'`

echo "$distro_name $distro_version"

echo "determining architecture..."
tmp_bits=`uname -m`
if [ "Xx86_64" == "X$tmp_bits" ]; then
    arch=""
else
    arch="-i386"
fi
echo $arch
echo "done"

if [ "X$AGENT_BASE_URL" == "X" ]; then
    base_url="https://s3.amazonaws.com/dcmagentunstable"
else
    base_url=$AGENT_BASE_URL
fi

fname="dcm-agent-$distro_name"-$distro_version"$arch.$pkg_ext"

echo "Starting the installation process..."

# Detect an existing agent and kill it.

# Install agent.
install_agent $base_url $fname

# Create configuration file.
if [ "X$1" == "X" ]; then
    echo /opt/dcm-agent/embedded/bin/dcm-agent-configure -i --base-path /dcm
    /opt/dcm-agent/embedded/bin/dcm-agent-configure -i --base-path /dcm
    # Install optional packages.
    install_chef_client
else
    echo /opt/dcm-agent/embedded/bin/dcm-agent-configure $@
    /opt/dcm-agent/embedded/bin/dcm-agent-configure $@
fi


# Notification for non-native packages.
if [[ $platform != 'ubuntu' ]]; then
    echo "========================================================================================="
    echo "[ALERT] secure-delete was not installed since it is not natively available in ${platform}."
    echo "[ALERT] If you want to make secure-delete functional, please download and install it."
    echo "[ALERT] http://sourceforge.net/projects/srm/"
    echo "========================================================================================="
fi

echo "To start the agent now please run:"
echo " /etc/init.d/dcm-agent start"

