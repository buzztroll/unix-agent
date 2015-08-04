=========
dcm-agent
=========

Introduction
============

The dcm-agent is an open source python project for use with the Dell Cloud
Manager (DCM).  When installed inside of a virtual machine that is launched
using DCM it gives DCM system level control over the VM instance and thus
allows for the automated creation, monitoring, and control of sophisticated
cloud applications.  Some of the features that it provides are:

- Server health monitoring
- Automated software installation/configuration
- Adding/removing users
- Disk volume management

The internal workings of the dcm-agent and its interactions with DCM are
outside of the scope of this document.  However we will present some general
information on how the agent works in order to assist in trouble shooting.

Installation
============

To install the agent from the this source do the following:

pip install .

Installation of Docker Extensions
============

To install the docker extensions from the this source do the following:

pip install -r extensions/docker/dcmdocker/requirements.txt
pip install -r extensions/docker/dcmdocker/test-requirements.txt
python extensions/docker/dcmdocker/setup.py install

Configure
=========

The safest way to configure the agent is with the configuration tool which can
be found at /opt/dcm-agent/agentve/bin/dcm-agent-configure

New Configuration
-----------------

When installing the agent to a new system it is easiest to use interactive
mode.  To use this run the configuration tool with the -i option.  This will
prompt you with questions to answer.

For those looking to automate an installation needed options can be set from
the command line instead.  The needed options are:

  --cloud {Amazon, etc...}, -c {Amazon, etc...}
                        The cloud where this virtual machine will be run.
                        Options: Amazon, Atmos, ATT, Azure, Bluelock,
                        CloudCentral, CloudSigma, CloudStack, CloudStack3,
                        Eucalyptus, GoGrid, Google, IBM, Joyent, OpenStack,
                        Rackspace, ServerExpress, Terremark, VMware, Other

  --url URL, -u URL     The location of the DCM web socket listener

  --base-path BASE_PATH, -p BASE_PATH The directory to which the agent should
                                      be installed.

This program will create a directory structure under <BASE_PATH>.  In it you
will find the file <BASE_PATH>/etc/agent.conf.  This file contains information
about your agent installation.

Re-configure
------------

The dcm-agent-configure program can also be used to update an agent
configuration.  Once installed
dcm-agent-configure -r <BASE_PATH>/etc/agent.conf
can be used.  This will read in the current configuration and use all of its
values as defaults.  Any other passed in command line options or answers to
interactive questions will override these defaults.

Manual Configuration
--------------------

The file <BASE_PATH>/etc/agent.conf holds most of the configuration
information.  It should only be edited with great care.  In the file many key
value pairs can be found and altered.  One of the safer options to alter is the
logging configuration.  The value configfile under the section [logging] points
to a file which contains various logging settings.  By default that file is
/dcm/etc/logging.yaml. This file is where log levels and paths to logging files
can be changed.

After installing the agent and configuring it with the dcm-agent-configuration
tool, you can make further customization by editing the file
/dcm/etc/agent.conf

Architecture
============

Web Sockets
-----------

The agent connects to the agent manager using websockets.  The connection
direction is always out, thus no inbound ports need to be opened up on your
server and it is NAT friendly.  When the agent starts it creates a thread of
execution which periodically attempts to form a connection with DCM.  Once that
connection is formed commands can be received from DCM and executed by the
agent.  Further the agent can respond to completed commands and can log
information back to DCM.

If a websocket connection is ever lost the agent will periodically attempt to
re-connect.  This is a normal part of the agent's execution.  Websocket
connections will time out from being idle, or DCM may close them, or a network
partition may happen.  The agent is tolerant of all such situations.

Idempotent
----------

Every command executed by the dcm-agent comes with a globally unique
identifier.  This ID is used to make sure that the agent executes any command
at most 1 time.  The commands and identifiers are kept in a sqlite database
file.  Because of this the agent system can surive reboots.
