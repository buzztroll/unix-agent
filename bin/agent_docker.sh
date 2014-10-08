#!/usr/bin/env bash

#************************
# set and uncomment the below variables to customize your install
#************************
#AGENT_BASE_URL=
#AGENT_UNSTABLE=
#AGENT_VERSION=
#DCM_HOST=ec2-54-185-194-247.us-west-2.compute.amazonaws.com
#DCM_CLOUD=Amazon
#DCM_DOCKER_PULL_REPOS=
DCM_DOCKER_VERSION=1.2.0
#************************


set -e
 
function update(){
    case $DCM_AGENT_FORCE_DISTRO_VERSION in
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

function install_agent() {
    cd /tmp

    if [ "X$AGENT_BASE_URL" == "X" ]; then
        AGENT_BASE_URL="https://s3.amazonaws.com/dcmagentdockerdemo"
    fi
    export AGENT_BASE_URL

    installer_url="$AGENT_BASE_URL""/installer.sh"
    curl $installer_url > installer.sh
    chmod 755 installer.sh

    if [[ "X$DCM_CLOUD" != "X" || "X$DCM_HOST" != "X" ]]; then
        echo 'Agent being installed with cloud parameter: ' $DCM_CLOUD
        echo 'Agent being installed with dcm host: ' $DCM_HOST
        ./installer.sh --base-path /dcm --cloud $DCM_CLOUD --url wss://$DCM_HOST:16433/ws
    else
        ./installer.sh --base-path /dcm
    fi

    /etc/init.d/dcm-agent start
    if [ $? -eq 0 ]; then
        echo 'The agent service has started'
    fi
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

    export DCM_AGENT_FORCE_DISTRO_VERSION="$distro_name""-""$distro_version"
}

function install_docker() {
    case $DCM_AGENT_FORCE_DISTRO_VERSION in
        ubuntu-14.04)
            sudo apt-get -y install docker.io $DCM_DOCKER_VERSION
            sudo ln -sf /usr/bin/docker.io /usr/local/bin/docker
            sudo sed -i '$acomplete -F _docker docker' /etc/bash_completion.d/docker.io
            ;;

        debian-7.*|ubuntu-12.04)
            DEBIAN_FRONTEND=noninteractive

            # aufs is preferred over devicemapper; try to ensure the driver is available.
            if ! grep -q aufs /proc/filesystems && ! $sh_c 'modprobe aufs'; then
                kern_extras="linux-image-extra-$(uname -r)"
                    ( set -x; $sh_c 'sleep 3; apt-get install -y -q '"$kern_extras" ) || true

                    if ! grep -q aufs /proc/filesystems && ! $sh_c 'modprobe aufs'; then
                        echo >&2 'Warning: tried to install '"$kern_extras"' (for AUFS)'
                        echo >&2 ' but we still have no AUFS.  Docker may not work. Proceeding anyways!'
                        ( set -x; sleep 10 )
                    fi
            fi

            if [ ! -e /usr/lib/apt/methods/https ]; then
                    ( set -x; $sh_c 'sleep 3; apt-get install -y -q apt-transport-https' )
            fi
            if [ -z "$curl" ]; then
                    ( set -x; $sh_c 'sleep 3; apt-get install -y -q curl' )
                    curl='curl -sSL'
            fi
            (
                set -x
                if [ "https://get.docker.io/" = "$url" ]; then
                    $sh_c "apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9"
                elif [ "https://test.docker.io/" = "$url" ]; then
                    $sh_c "apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 740B314AE3941731B942C66ADF4FD13717AAD7D6"
                else
                    $sh_c "$curl ${url}gpg | apt-key add -"
                fi
                $sh_c "echo deb ${url}ubuntu docker main > /etc/apt/sources.list.d/docker.list"
                $sh_c 'sleep 3; apt-get update -y; apt-get install -y -q lxc-docker$DCM_DOCKER_VERSION'
            )
            ;;

        centos-6.5)
            sudo yum -y install epel-release
            sudo yum -y install docker-io$DCM_DOCKER_VERSION
            sudo service docker start
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
#        sudo docker pull ubuntu
    fi

}

function help() {
    echo "
         **************************************************
         usage:  bash agent_docker.sh -o/--option=<value>
       
         Here are the possible options:
         -h/--help         show this help menu
         -d/--dcm          sets DCM_HOST
         -a/--agenturl     sets AGENT_BASE_URL default=https://s3.amazonaws.com/dcmagentnigthly
         -v/--version      sets AGENT_VERSION
         -c/--cloud        sets DCM_CLOUD
         -u/--unstable     sets AGENT_UNSTABLE
         **************************************************"
}

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
              DCM_HOST="${arg#*=}"
              ;;
            -a=*|--agenturl=*)
              AGENT_BASE_URL="${arg#*=}" 
              ;;
            -v=*|--version=*)
              AGENT_VERSION="${arg#*=}"
              ;;
            -c=*|--cloud=*)
              DCM_CLOUD="${arg#*=}"
              ;;
            -u=*|--unstable=*)
              AGENT_UNSTABLE="${arg#*=}"
              ;;
            *)
              echo 'You passed an unknow option:' $arg
              echo 'run agent_docker.sh --help for more info'
              exit
        esac
    done
fi

url='https://get.docker.io/'
#user="$(id -un 2>/dev/null || true)"

sh_c='sh -c'
if [ "$user" != 'root' ]; then
    if command_exists sudo; then
        sh_c='sudo sh -c'
    elif command_exists su; then
        sh_c='su -c'
    else
        echo >&2 'Error: this installer needs the ability to run commands as root.'
        echo >&2 'We are unable to find either "sudo" or "su" available to make this happen.'
        exit 1
    fi
fi

identify_platform
update

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

if docker_exists; then
    echo >&2 'Warning: "docker" or "lxc-docker" command appears to already exist.'
else
    echo '**************************************'
    echo 'Proceeding with installation of Docker'
    echo '**************************************'
    install_docker
fi

if agent_exists; then
    echo  'python agent is already installed'
else
    echo '**************************************'
    echo 'Proceeding with installation of Agent' 
    echo '**************************************'
    install_agent
fi   


echo
echo 'Adding dcm to docker group'
sudo usermod -aG docker dcm
echo
echo 'Remember that you will have to log out and back in for this to take effect!'
echo 'Install is complete'

