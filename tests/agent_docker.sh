#!/usr/bin/env bash
 
cd /tmp
apt-get update -y
apt-get install -y curl
yum install -y curl
curl https://s3.amazonaws.com/dcmagentunstable/installer.sh > installer.sh
chmod 755 installer.sh
export AGENT_BASE_URL=https://s3.amazonaws.com/dcmagentnightly
./installer.sh --base-path /dcm #--cloud @@DCM_CLOUD@@ --url wss://$DCM_HOST:16433/ws
/etc/init.d/dcm-agent start
 
 
set -e
 
url='https://get.docker.io/'
user="$(id -un 2>/dev/null || true)"

function command_exists() {
    command -v "$@" > /dev/null 2>&1
}
 
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

function install_docker() {
    identify_platform

    if command_exists docker || command_exists lxc-docker; then
            echo >&2 'Warning: "docker" or "lxc-docker" command appears to already exist.'
            echo >&2 'Please ensure that you do not already have docker installed.'
            echo >&2 'You may press Ctrl+C now to abort this process and rectify this situation.'
            ( set -x; sleep 20 )
    fi
        
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

    case $DCM_AGENT_FORCE_DISTRO_VERSION in
        ubuntu-14.04)
            sudo apt-get update
            sudo apt-get -y install docker.io
            sudo ln -sf /usr/bin/docker.io /usr/local/bin/docker
            sudo sed -i '$acomplete -F _docker docker' /etc/bash_completion.d/docker.io

            if command_exists docker && [ -e /var/run/docker.sock ]; then
                    (
                            set -x
                            $sh_c 'docker run hello-world'
                    ) || true
            fi

            ;;

        debian-7.*|ubuntu-12.04)
            DEBIAN_FRONTEND=noninteractive

            did_apt_get_update=
            apt_get_update() {
                  if [ -z "$did_apt_get_update" ]; then
                          ( set -x; $sh_c 'sleep 3; apt-get update' )
                          did_apt_get_update=1
                  fi
            }

            # aufs is preferred over devicemapper; try to ensure the driver is available.
            if ! grep -q aufs /proc/filesystems && ! $sh_c 'modprobe aufs'; then
                    kern_extras="linux-image-extra-$(uname -r)"

                    apt_get_update
                    ( set -x; $sh_c 'sleep 3; apt-get install -y -q '"$kern_extras" ) || true

                    if ! grep -q aufs /proc/filesystems && ! $sh_c 'modprobe aufs'; then
                            echo >&2 'Warning: tried to install '"$kern_extras"' (for AUFS)'
                            echo >&2 ' but we still have no AUFS.  Docker may not work. Proceeding anyways!'
                            ( set -x; sleep 10 )
                    fi
            fi

            if [ ! -e /usr/lib/apt/methods/https ]; then
                    apt_get_update
                    ( set -x; $sh_c 'sleep 3; apt-get install -y -q apt-transport-https' )
            fi
            if [ -z "$curl" ]; then
                    apt_get_update
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
                  $sh_c 'sleep 3; apt-get update; apt-get install -y -q lxc-docker'
            )

            if command_exists docker && [ -e /var/run/docker.sock ]; then
                    (
                            set -x
                            $sh_c 'docker run hello-world'
                    ) || true
            fi
            ;;

        centos-6.5)
            sudo yum -y install epel-release
            sudo yum -y install docker-io
            sudo service docker start
            if command_exists docker && [ -e /var/run/docker.sock ]; then
                    (
                            set -x
                            $sh_c 'docker run hello-world'
                    ) || true
            fi
            ;;

        *)
            Echo "Sorry we could not install docker"
            echo "Docker is not available for this platform"
            echo "Please see http://docs.docker.com/installation/ for detailed information on supported platforms"
            exit 1
            ;;
    esac
}


if [ "$user" != 'root' ]; then
    echo
    echo 'Adding' $user 'to docker group'
    sudo usermod -aG docker $user
    echo
    echo 'Remember that you will have to log out and back in for this to take effect!'
    echo 'Install is complete'
fi
install_docker
