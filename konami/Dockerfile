FROM phusion/baseimage:0.9.15

ENV HOME /root
ENV DCM_AGENT_PRE_START_SLEEP 0

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh
RUN /usr/bin/workaround-docker-2267

CMD ["/sbin/my_init"]

EXPOSE 22

RUN apt-get update -y
RUN apt-get install -y curl
RUN mkdir -p /root/dcmagent
ADD env.sh /root/dcmagent/env.sh
ADD bootstrap.sh /root/dcmagent/bootstrap.sh
RUN /root/dcmagent/bootstrap.sh 

ADD rename /dcm/bin/rename

