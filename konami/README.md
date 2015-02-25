#Konami Testing with Agent Support

## Basic Idea

GOAL:  Add Agents to Konami server instances.

As Konami instances are neither bare metal nor virtual, the challenge is running an agent where no CPU exist.
The current strategy is to proxy agents.  Developers running the es-onpremise-chef-solo vagrant stack add
docker to that stack.  Docker then runs individual agent proxy containers per Konami vm.

SUMMARY OF STEPS:

1. Modify Vagrant to run Ubuntu 14.04 LTS (adds kernel namespace support).
2. Modify Vagrant to run docker daemon.
3. Clone the es-ex-pyagent repo to dcm/es-onpremise-chef-solo.  `This merits a discussion.`
4. Build the agent docker image.
5. Use the Java harness to launch agents as needed in test code.

## Details

### Use Ubuntu 14.04 LTS on Vagrant

Set ES_BOX before Vagrant launches.

    export ES_BOX=http://opscode-vm-bento.s3.amazonaws.com/vagrant/virtualbox/opscode_ubuntu-14.04_chef-provisionerless.box

### Expose Docker API

Edit dcm/es-onpremise-chef-solo/Vagrantfile.  Add a line like the one below.  I avoided using the host 2375 in
favor of 22375.

    config.vm.network :forwarded_port, guest: 2375, host: 22375   # Docker REST

### Clone es-ex-pyagent on DEV (i.e. OSX)

Checkout the es-ex-pyagent repo on the VirtualBox shared drive.  We use the shared drive because (a) the
repo provides a bleeding edge build for our agent Dockerfile (b) the repo continues to work correctly on
the developer's machine (c) all without any ssh key games.  If the need for 'bleeding edge' is eliminated,
the agent build could alternatively be packaged.

    cd dcm/es-onpremise-chef-solo/
    git clone git@github.com:enStratus/es-ex-pyagent.git
    
### Build the Docker agent image.

This command should be in the dcm/es-onpremise-chef-solo.  It assumes all the default environment
variables are acceptable.

    vagrant ssh -- '(cd /vagrant/es-ex-pyagent/konami && sudo ./build-image.sh)'

### Alternatively, build the Docker agent with a custom environment.

This should not be needed in most cases.

    vagrant ssh -- 'sudo VAR1=val1 VAR2=val2 bash -c "(cd /vagrant/es-ex-pyagent/konami && ./test.sh)"'

Here's a list with their defaults:

AGENT_BASE_URL=https://s3.amazonaws.com/dcmagentnightly
DCM_AGENT_CLOUD=Konami
DCM_AGENT_URL="wss://172.16.129.19:443/agentManager"
DCM_AGENT_PRE_START_SLEEP=0
DCM_AGENT_SSH_KEY="changeme"
DCM_KONAMI_INSTANCE_ID="changeme"


### Manually running an agent:
All of these commands should be run from a vagrant ssh prompt as root.

    # Start an agent container
    docker run -d \
        -e DCM_AGENT_URL=wss://172.16.129.19/agentManager \
        -e DCM_AGENT_CLOUD=Konami \
        -e DCM_KONAMI_INSTANCE_ID="vmb850d156-2c8c-4aea-9cf1-b9b8fa8aae66" \
        -e DCM_KONAMI_PRIVATE_IP=192.168.0.1 \
        -e DCM_KONAMI_PUBLIC_IP=10.0.0.1 \
        -P konamiagent

    # Look for newly created container
    docker

    # Output should be similar to this...
    # CONTAINER ID   IMAGE              COMMAND         ...
    # 83137004bcfe   konamiagent:latest /sbin/my_init   ...   0.0.0.0:49153->22/tcp

    # Get a root shell
    docker exec -i -t 83137 bash

    # From inside the container, you can now get more debugging leverage if needed.
    # root@83137004bcfe:~# apt-get update
    # root@83137004bcfe:~# apt-get install tcpdump
    # and so forth

### Docker cleanup

This script will bring Docker (close) to a clean slate.  Obviously use with caution.  This is
handy in a dev environment.

    vagrant ssh -- '(cd /vagrant/es-ex-pyagent/konami && sudo ./nuke-docker.sh)'


### Ports

This is just info.  No action is needed here.

Docker has some IANA assigned ports.
- 2375 - REST API for docker management (plain text)
- 2376 - REST API for docker management (encrypted)

If the instructions above were followed...

Vagrant is running docker and docker is listening to port 2375.

    root@vagrant:~# netstat -atunp | egrep "2375 .*LISTEN"
    tcp        0      0 0.0.0.0:2375            0.0.0.0:*               LISTEN      655/docker.io


We're forwarding 2375 out to 22375 (notice the extra 2).  This avoids any issues running other docker
stuff on the development machine (boot2docker for OSX, docker for CentOS7, etc) which may already be
listening to 2375.

    brians-mbp-2:es-onpremise-chef-solo bfox$ netstat -an | egrep "22375 .*LISTEN"
    tcp4       0      0  *.22375                *.*                    LISTEN





