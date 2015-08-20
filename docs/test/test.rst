Testing DCM Agent For Linux
===========================

This document covers how to run tests locally for
development purposes.

Local development tests are supported by `Vagrant <https://www.vagrantup.com/>`_.  You will
find a multi machine Vagrantfile located in :samp:`src/dcm/agent/tests`.  Running the test
suite on a particular distribution is as simple as going to that directory and running
:samp:`vagrant up <machine name>` .  You can get a list of available machine names by running
:samp:`vagrant status`.

Vagrant up provisions the image with an agent and runs the tests suite with coverage.  You
will see the output in your terminal.

The following environment variables can be set to customize the test environment.

.. code-block:: text

    TEST_AGENT_STORAGE_CREDS
    TEST_AGENT_VERSION
    TEST_AGENT_BASE_URL
    TEST_AGENT_LOCAL
    TEST_AGENT_DOCKER_INSTALL

1. :samp:`TEST_AGENT_STORAGE_CREDS` is optional and should point to a local file with entries listed like so
    and enables a subset of tests dealing with mount/unmount commands to run.::

    1 <aws_access_key> <aws_secret_key> us_west_oregon


2. :samp:`TEST_AGENT_VERSION` is optional and lets you explicitly set the version to test.

3. :samp:`TEST_AGENT_BASE_URL` is optional and lets you explicitly set where to get the agent package to test.

4. :samp:`TESTS_AGENT_LOCAL` is optional and runs the test suite against the local source code.

5. :samp:`TEST_AGENT_DOCKER_INSTALL` is optional and provisions the VM with the `agent_docker` script.

Running Tests Manually
======================

You can alternatively run the tests manually in the VM after the VM is in a running state.

Simply :samp:`vagrant ssh <machinename>` and do

.. code-block:: bash

    $ sudo -i
    $ source /opt/dcm-agent/embedded/agentve/bin/activate
    $ nosetests -v dcm.agent.tests


Using a Remote Debugger
=======================

Coming Soon!