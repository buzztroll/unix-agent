Installing and Configuring the DCM Agent
========================================

In most cases the DCM Agent should be installed via the installer script
which can be found `here <http://linux.stable.agent.enstratius.com/installer.sh>`_.
This bash script will diagnose the system on which it is running to determine
the Linux distribution on which it is run.  It will then use that information
do download, install, and configure one of the packages in the
`stable repository <http://linux.stable.agent.enstratius.com>`_.   These
packages are created with `omnibus <https://github.com/chef/omnibus>`_
and contain the full stack of software needed for the agent including
python 3.4.

For information on various install options run the installer.sh script with
`--help`

Supported Linux Distributions
-----------------------------

The following Linux distributions are currently supported by the Linux DCM
Agent:

* Ubuntu 14.04 (amd64, i386)
* Ubuntu 12.04 (amd64, i386)
* Ubuntu 10.04 (amd64, i386)
* Debian 7.8 (amd64, i386)
* Debian 6.0 (amd64, i386)
* CentOS 7.0 (x86_64)
* CentOS 6.5 (x86_64, i386)
* CentOS 6.4 (i386)
* RHEL 7.1 (x86_64)
* RHEL 7.0 (x86_64)
* RHEL 6.5 (x86_64)
* RHEL 6.4 (x86_64)


Manual Installation
-------------------

Although it is not recommended or officially supported, the dcm-agent can be
installed manually into a python 3.4 virtual environment by running the
following commands in the src directory:

.. code-block:: bash

   $ pip install .

One installed the program `dcm-agent-configure` must be run in order to
properly setup the system for use with the agent.  To use this run the
configuration tool with the -i option.  This will prompt you with questions to
answer.

.. code-block:: bash

   $ dcm-agent-configure -i

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

Running dcm-agent
-----------------

One the agent is installed and configured, whether it be manually or via the
installer, the agent can be started with the following command:

.. code-block:: bash

   $ /etc/init.d/dcm-agent start


