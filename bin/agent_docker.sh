#!/usr/bin/env bash

#************************
# set and uncomment the below variables to customize your install
#************************
#AGENT_BASE_URL=
#AGENT_UNSTABLE=
#AGENT_VERSION=
#
#
#DCM_URL=wss://<hostname>/agentManager
#  or if running on older installation
#DCM_URL="wss://<hostname>:16433/ws"
#
#DCM_DOCKER_PULL_REPOS=ubuntu
#DCM_DOCKER_VERSION=1.2.0
#************************

if [ $DCM_DOCKER_VERSION -z ]; then
    export DCM_DOCKER_VERSION=1.9.1
fi

set -e

if [ "X$DCM_URL" == "X" ]; then
    DCM_URL="wss://dcm.enstratius.com/agentManager"
fi


function update(){
    case $DCM_DISTRO_VERSION in
        centos*)
            yum install -y curl
            ;;
        *)
            apt-get update -y
            apt-get install -y curl
            ;;
    esac
}

function command_exists() {
    command -v "$@" > /dev/null 2>&1
}

function docker_exists() {
    if command_exists docker || command_exists lxc-docker; then
        return 0

    else
        return 1
    fi
} 

function agent_exists() {
    if [ -d "/dcm" ]; then
        return 0
    else
        return 1
    fi
}


function agent_properly_configured() {
    OLD_DCM_URL=`grep agentmanager_url /dcm/etc/agent.conf | awk -F= '{ print $2 }'`
    if [ "X$OLD_DCM_URL" != "X$DCM_URL" ]; then
        return 1
    fi

    if ! docker_exists; then
        return 1
    fi

    proc_count=`ps -u dcm | grep dcm-agent | wc -l`
    if [ $proc_count -ne 2 ]; then
        return 1
    fi
    return 0
}


function install_agent() {
    cd /tmp

    if [ "X$AGENT_BASE_URL" == "X" ]; then
        AGENT_BASE_URL="https://s3.amazonaws.com/dcmagentunstable"
    fi
    export AGENT_BASE_URL

    installer_url="$AGENT_BASE_URL""/installer.sh"
    curl $installer_url > installer.sh
    chmod 755 installer.sh

    echo 'Agent being installed with dcm host: ' $DCM_URL
    ./installer.sh --base-path /dcm --url $DCM_URL $AGENT_UNVERIFIED -B
}

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

    DCM_DISTRO_VERSION="$distro_name""-""$distro_version"
}

function reconfigure_agent() {
   set +e
   /etc/init.d/dcm-agent stop
   pkill -9 dcm-agent
   rm -f /dcm/etc/agentdb.sql
   set -e
   /opt/dcm-agent/embedded/agentve/bin/dcm-agent-configure --base-path /dcm --url $DCM_URL $AGENT_UNVERIFIED -B
}

function install_docker() {
    url='https://get.docker.io/'

    case $DCM_DISTRO_VERSION in
        ubuntu-14.04)
            apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9
            echo deb https://get.docker.com/ubuntu docker main> /etc/apt/sources.list.d/docker.list
            apt-get update -y
            apt-get install -y lxc-docker-$DCM_DOCKER_VERSION
            ;;

        debian-7.*|ubuntu-12.04)
            DEBIAN_FRONTEND=noninteractive

            # aufs is preferred over devicemapper; try to ensure the driver is available.
            if ! grep -q aufs /proc/filesystems && ! modprobe aufs; then
                kern_extras="linux-image-extra-$(uname -r)"
                    ( set -x; sleep 3; apt-get install -y -q "$kern_extras" ) || true

                    if ! grep -q aufs /proc/filesystems && ! modprobe aufs; then
                        echo >&2 'Warning: tried to install '"$kern_extras"' (for AUFS)'
                        echo >&2 ' but we still have no AUFS.  Docker may not work. Proceeding anyways!'
                        ( set -x; sleep 10 )
                    fi
            fi

            if [ ! -e /usr/lib/apt/methods/https ]; then
                    ( set -x; sleep 3; apt-get install -y -q apt-transport-https )
            fi
            if [ -z "$curl" ]; then
                    ( set -x; sleep 3; apt-get install -y -q curl )
                    curl='curl -sSL'
            fi
            (
                set -x
                if [ "https://get.docker.io/" = "$url" ]; then
                    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9
                elif [ "https://test.docker.io/" = "$url" ]; then
                    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 740B314AE3941731B942C66ADF4FD13717AAD7D6
                else
                    $curl ${url}gpg | apt-key add -
                fi
                echo deb ${url}ubuntu docker main > /etc/apt/sources.list.d/docker.list
                sleep 3; apt-get update -y; apt-get install -y -q lxc-docker-$DCM_DOCKER_VERSION
            )
            ;;

        centos-6.5)
            yum -y install epel-release
            yum -y install docker-io$DCM_DOCKER_VERSION
            service docker start
            ;;
        
        *)
            echo "Sorry we could not install docker"
            echo "Docker is not available for this platform"
            echo "Please see http://docs.docker.com/installation/ for detailed information on supported platforms"
            exit 1
            ;;
    esac

    if docker_exists; then
        echo '**************************************'
        echo 'Docker has been successfully installed'
        echo '**************************************'

        if [ "X$DCM_DOCKER_PULL_REPOS" != "X" ]; then
            for r in $DCM_DOCKER_PULL_REPOS; do
                docker pull $r
            done
        fi
    fi

}

function help() {
    echo "
         **************************************************
         usage:  bash agent_docker.sh -o/--option=<value>
       
         Here are the possible options:
         -h/--help         show this help menu
         -d/--dcm          sets DCM_URL
         -a/--agenturl     sets AGENT_BASE_URL default=https://s3.amazonaws.com/dcmagentnigthly
         -v/--version      sets AGENT_VERSION
         -u/--unstable     sets AGENT_UNSTABLE
         **************************************************"
}

AGENT_UNVERIFIED=""
################# main ###################
if [ $# -lt 1 ]; then
    echo
    echo '***********************************'
    echo 'Running with default options intact'
    echo '***********************************'
    echo
else
    for arg in "$@"
    do
        case $arg in
            -h|--help)
              help
              exit 
              ;;
            -d=*|--dcm=*)
              DCM_URL="${arg#*=}"
              ;;
            -a=*|--agenturl=*)
              AGENT_BASE_URL="${arg#*=}" 
              ;;
            -v=*|--version=*)
              AGENT_VERSION="${arg#*=}"
              ;;
            -u=*|--unstable=*)
              AGENT_UNSTABLE="${arg#*=}"
              ;;
            -Z)
              AGENT_UNVERIFIED="-Z"
              ;;
            *)
              echo 'You passed an unknown option:' $arg
              echo 'run agent_docker.sh --help for more info'
              exit
        esac
    done
fi

url='https://get.docker.io/'

identify_platform

case "$(uname -m)" in
    *64)
        ;;
    *)
        echo >&2 'Error: you are not using a 64bit platform.'
        echo >&2 'Docker currently only supports 64bit platforms.'
        echo "Please see http://docs.docker.com/installation/ for detailed information on supported platforms"
        exit 1
        ;;
esac

if agent_exists; then
    if agent_properly_configured; then
        echo "The agent is installed properly and running"
        exit 0
    else
        echo 'Reconfiguring with the new values'
        reconfigure_agent
    fi
    update
else
    echo '**************************************'
    echo 'Proceeding with installation of Agent'
    echo '**************************************'
    update
    install_agent
fi

if docker_exists; then
    echo >&2 'Warning: "docker" or "lxc-docker" command appears to already exist.'
    found_version=`docker --version | awk '{ print $3 }' | sed 's/,//'`
    if [ "X$found_version" != "X$DCM_DOCKER_VERSION" ]; then
        echo '*******************************************************************'
        echo "Upgrading Docker from version $found_version to $DCM_DOCKER_VERSION"
        echo '*******************************************************************'
        install_docker
    fi
else
    echo '**************************************'
    echo 'Proceeding with installation of Docker'
    echo '**************************************'
    install_docker
fi

echo
echo 'Adding dcm to docker group'
usermod -aG docker dcm

if [ -e /etc/init.d/dcm-agent ]; then
    /etc/init.d/dcm-agent start
    if [ $? -eq 0 ]; then
        echo 'The agent service has started'
    fi
fi

echo
echo 'Remember that you will have to log out and back in for this to take effect!'
echo 'Install is complete'
