FROM phusion/baseimage:0.9.6

ENV HOME /root

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

CMD ["/sbin/my_init"]

RUN apt-get update -y
RUN mkdir -p /agent/pkg
ADD pkg /agent/pkg
ADD install-agent.sh /agent/pkg/
RUN cd /agent/pkg; ./install-agent.sh
RUN /usr/sbin/enable_insecure_key

RUN mkdir -p /etc/service/es-ex-pyagent
ADD runagent.sh /etc/service/es-ex-pyagent/run

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
