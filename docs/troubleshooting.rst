Agent Troubleshooting
======================

At times users may experience problems with the agent.  Here we will explain
some troubleshooting steps that may help diagnose and fix common problems.

* Gather agent information.  In order to receive help from the DCM support team
  it is helpful to provide information about your installed agent.  The DCM
  Agent is bundled with a tool that will gather the needed information put it
  into a tarball.  To create this tarball run the following:

  .. code-block:: bash

     % sudo /opt/dcm-agent/embedded/agentve/bin/dcm-agent --report
     **********************************************************************
     To get all log and configuration files copy /tmp/agent_info.tar.gz to
     your local machine
     **********************************************************************

  When reporting a problem please include this tarball.

* Inspect the logs.  Useful information about the dcm-agent's execution is
  written to the file /dcm/log/agent.log.  This file can be inspected for error
  messages and other useful information.

* Increase the log level.  By default the dcm-agent logs at the "INFO" level.
  At times it may be useful to increase the level to DEBUG.  This will result
  in very verbose logging and may provide the information needed.  Note that
  doing this can cause passwords to be logged in /dcm/logs/agent.log.wire.
  To increase the log level do the following:


  * Edit /dcm/etc/logging.yaml
  * Change occurrences of INFO to DEBUG
  * restart the agent:

    .. code-block:: bash

       % sudo /etc/init.d/dcm-agent restart

  * Verify the agent manager URL.  During normal operation the dcm-agent forms
    a TCP connection with DCM.  If this connection cannot be made the dcm-agent
    will not work.  The contact point is set in the file
    */dcm/etc/agent.conf* under the setting *agentmanager_url=<URL>*.
    Verify that the value of URL is correct.  In most cases it should start
    with *wss://* (note the difference between that and *ws://*).  Even in
    cases when the URL is correct there may be a firewall blocking the
    connection from happening.  To verify that a connection can be made from
    your VM to DCM run the following:

    .. code-block:: bash

        % telnet <URL host> <URL port>
        Trying 1.2.3.4...
        Connected to example.com.
        Escape character is '^]'.
        ^]quit

  * Inspect wire logs.  When logging is turned to DEBUG in all
    loggers the JSON documents that are sent across the wire will be written
    to the file /dcm/logs/agent.log.wire.  This infomation can be helpful
    for debugging the agents interactions with DCM.  Note that the information
    written to this log is raw and thus passwords may be written in clear text.
    This logging is off by default.

  * Inspect job runner logs.  Scripts are forked and executed by the agent
    as part of its normal processing.  Details about the parameters sent
    to these scripts and the output and exit codes from there scripts are
    logged at /dcm/logs/agent.log.job_runner.  This information can be useful
    when debugging errors in agent's commands.
