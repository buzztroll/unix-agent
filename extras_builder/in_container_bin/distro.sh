#!/bin/bash

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
        Fedora)
            platform="el"
            distro_version=$(echo $redhat_info | awk '{print $3}')
            distro_name="fedora"
            pkg_ext="rpm"
            installer_cmd="rpm -Uvh"
        ;;
        *)
            echo "Sorry we could not detect your environment"
            exit 1
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

distro_version=`echo $distro_version | awk -F '.' '{ print $1 }'`

tmp_bits=`uname -m`
if [ "Xx86_64" == "X$tmp_bits" ]; then
    if [[ "X$distro_name" == "Xcentos" || "X$distro_name" == "Xrhel" || "X$distro_name" == "Xfedora" ]]; then

         arch="x86_64"
    else
         arch="amd64"
    fi
else
    arch="i386"
fi

echo "$distro_name-$distro_version-$arch" $pkg_ext
