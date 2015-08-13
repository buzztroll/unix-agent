.. _configure:

Configuration
-------------

The installer configures the agent initially, but the configuration values can be
changed without reinstalling the agent.

One installed the program `dcm-agent-configure` can be run in order to (re)set the values
in the configuration file.

You can do this interactively or by explicitly passing arguments.
To run the configuration tool interactively pass it the -i option.  This will prompt you with questions to
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

The dcm-agent-configure program can also be used to update an installed agent's
configuration.  To reconfigure run

.. code-block:: python

   $ dcm-agent-configure -r <BASE_PATH>/etc/agent.conf


This will read in the current configuration and use all of its
values as defaults.  Any other passed in command line options or answers to
interactive questions will override these defaults.
