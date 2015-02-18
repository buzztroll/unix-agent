FROM centos:centos6

ENV HOME /root
EXPOSE 22

RUN rpm -ivh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
RUN yum install -y centos-release-SCL

RUN yum install -y curl s3cmd \
    autoconf \
    bison \
    flex \
    gcc \
    gcc-c++ \
    kernel-devel \
    make \
    m4 \
    patch \
    openssl-devel \
    expat-devel \
    perl-ExtUtils-MakeMaker \
    curl-devel \
    tar \
    unzip \
    libxml2-devel \
    libxslt-devel \
    ncurses-devel \
    zlib-devel \
    rsync \
    rpm-build \
    fakeroot \
    git \
    ccache
RUN yum clean all

ADD omnibus-dcm-agent-extras /omnibus-dcm-agent-extras
ADD in_container_bin/build-upload.sh /bin/build-upload.sh
ADD in_container_bin/distro.sh /bin/distro.sh 
ADD in_container_bin/s3cfg /root/.s3cfg
