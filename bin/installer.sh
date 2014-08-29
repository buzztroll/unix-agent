#!/usr/bin/env bash
# DCM Agent Installer for Linux

SHELL_PID=$$
installer_cmd=""

function print_help() {
    echo "
This script will fetch and install the dcm-agent on the virtual machine where
it is run.  When run with no options it will detect the VM's Linux
distribution and download the appropriate stable package.  The following
environment variables will alter the behavior as described:

AGENT_LOCAL_PACKAGE=<path>
  - When set the script will look for the distribution package at the
    given path on the local file system.

AGENT_BASE_URL=<url>
  - This is the base path to an HTTP repository where the packages are kept.
    For example: https://s3.amazonaws.com/dcmagentunstable.  Packages will
    be found under that url with a name that matches:
    dcm-agent-<distribution>-<distribution version>-<architecture>.<pkg type>
    For example: dcm-agent-centos-6.5-amd64.deb

AGENT_UNSTABLE
  - When set the script will download and install the latest unstable version
    of the dcm-agent.

AGENT_VERSION
  - To download a specific version of the agent set this to the version.

DCM_AGENT_FORCE_DISTRO_VERSION
  - Instead of detecting the distribution version force it to this env string.
"

    echo "options:"
    echo "--unstable: download the latest unreleased packages."
}

if [ $# -gt 0 ]; then
    if [[ "X$1" == "X--help" || "X$1" == "X-h" ]]; then
        print_help
        exit 1
    fi;
fi

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
        echo "Downloading $url ..."
        curl -s -L $url > /tmp/$filename
    else
        if [[ $1 == *://* ]] ; then
            curl -s -L $AGENT_LOCAL_PACKAGE > /tmp/$filename
        else
            cp $AGENT_LOCAL_PACKAGE /tmp/$filename
        fi
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
        curl -s -L https://www.opscode.com/chef/install.sh | bash
        echo "Done."
    fi
}

# Identify platform.
function identify_platform() {
    if [ -x "/usr/bin/lsb_release" ]; then
        lsb_info=$(/usr/bin/lsb_release -i | cut -f2)
        distro_version=$(/usr/bin/lsb_release -r | cut -f2)
        case $lsb_info in
            "Ubuntu")
                distro_name="ubuntu"
                ;;
            "Debian")
                distro_name="debian"
                ;;
            "CentOS")
                distro_name="centos"
                ;;
            "RedHatEnterpriseServer")
                distro_name="rhel"
                ;;
            "SUSE LINUX")
                distro_name="suse"
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
                distro_version=$(echo $redhat_info | awk '{print $3}')
                distro_name="centos"
            ;;
            Red)
                distro_version=$(echo $redhat_info | awk '{print $4}')
                distro_name="rhel"
            ;;
        esac
    elif [ -f "/etc/debian_version" ]; then
        distro_version=$(cat /etc/debian_version)
        distro_name="debian"
    elif [ -f "/etc/SuSE-release" ]; then
        distro_version=$(cat /etc/issue | awk '{print $2}')
        distro_name="suse"
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

    export DCM_AGENT_FORCE_DISTRO_VERSION="$distro_name""-""$distro_version"
}

function set_installer() {
    case $DCM_AGENT_FORCE_DISTRO_VERSION in
        ubuntu*)
            platform="ubuntu"
            pkg_ext="deb"
            installer_cmd="dpkg -i"
            ;;
        debian*)
            platform="debian"
            pkg_ext="deb"
            installer_cmd="dpkg -i"
            ;;
        cent*)
            platform="el"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
            ;;
        rhel*)
            platform="el"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
            ;;
        suse*)
            platform="suse"
            pkg_ext="deb"
            installer_cmd="dpkg -i"
            ;;
        *)
            echo "Sorry we could not detect your environment"
            exit 1
            ;;
    esac
}

which curl > /dev/null
if [ $? -ne 0 ]; then
    echo "curl must be installed on your system to use this installer."
    exit 1
fi

if [ "X$DCM_AGENT_FORCE_DISTRO_VERSION" == "X" ]; then
    identify_platform
fi
echo $DCM_AGENT_FORCE_DISTRO_VERSION
set_installer

echo "determining architecture..."
tmp_bits=`uname -m`
if [ "Xx86_64" == "X$tmp_bits" ]; then
    if [ "X$distro_name" == "Xcentos" ]; then
         arch="-x86_64"
    else
         arch="-amd64"
    fi
else
    arch="-i386"
fi
echo $arch
echo "done"

if [[ "X$AGENT_BASE_URL" == "X" && "X$AGENT_BASE_URL" != "XNONE" ]]; then
    if [ "X$AGENT_UNSTABLE" != "X" ]; then
        base_url="https://s3.amazonaws.com/dcmagentunstable"
    else
        base_url="https://es-pyagent.s3.amazonaws.com"
    fi
else
    base_url=$AGENT_BASE_URL
fi

agent_version_ext=""
if [ "X$AGENT_VERSION" != "X" ]; then
    agent_version_ext="-$X$AGENT_VERSION"
fi

fname="dcm-agent-$DCM_AGENT_FORCE_DISTRO_VERSION$arch$agent_version_ext.$pkg_ext"

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

