FROM phusion/baseimage:0.9.15

ENV HOME /root
ENV DCM_AGENT_PRE_START_SLEEP 0
ENV DCM_AGENT_CLOUD Konami
ENV DCM_AGENT_SSH_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDdY8U2OGk91mcHrR6713sPDAtYoFeTyh9i513Aoh+QNuPGn4aX8AJB1Bm4H2wcsOT6KnU6yYqWa0WxJtxgcOmpsTQ8Cl//5e7KXD5cjYuE8NpebvOSNoC5oY3nbTBzoj+ioBjfGHJSZo95qjVC+W3a+NNTuXVNM4m5QTbt8BUQB2FHgJb5NCaPFkJ5U2tihMc3HzMouGHtAUlEc992Fc/jQTJ6LQH+GVsqpGdYBL1pqjMkegdPe3DlxW8g7dEtreDbZbtV3NKiQ6qjid/9MQba0aDW0/Vh7BxbamY8fbrI1QpW0pzR2R184wkSzHW1mASldhEpbOQJFFwnpsJ/yLZb bresnaha@Johns-MacBook-Pro.local"

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh
RUN /usr/bin/workaround-docker-2267

CMD ["/sbin/my_init"]

EXPOSE 22

RUN apt-get update -y
RUN apt-get install -y curl
RUN mkdir /tmp/agent_install
ADD env.sh /tmp/agent_install/env.sh
ADD install-agent.sh /tmp/agent_install/install-agent.sh
RUN /tmp/agent_install/install-agent.sh

ADD reconfigure-and-start-agent.sh /etc/my_init.d/99_reconfigure-and-start-agent.sh
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
