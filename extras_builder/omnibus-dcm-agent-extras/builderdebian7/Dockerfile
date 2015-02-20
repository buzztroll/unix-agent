FROM debian:wheezy


ENV HOME /root
EXPOSE 22

RUN apt-get update -y
RUN apt-get install -y curl s3cmd \
   git \
    curl \
    autoconf \
    binutils-doc \
    bison \
    flex \
    gettext \
    ncurses-dev \
    rsync \
    libyaml-dev \
    ccache \
    devscripts \
    dpkg-dev \
    fakeroot \
    build-essential \
    ruby1.9.1-full \
    libssl-dev \
    libreadline-dev \
    libxslt1-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    zlib1g-dev \
    libexpat1-dev \
    libicu-dev \
    unzip \
    m4 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* 

ADD omnibus-dcm-agent-extras /omnibus-dcm-agent-extras
ADD in_container_bin/build-upload.sh /bin/build-upload.sh
ADD in_container_bin/distro.sh /bin/distro.sh 
ADD in_container_bin/s3cfg /root/.s3cfg
