.. raw:: latex
  
      \newpage

.. _agent_noninteractive_install:

Non-interactive Install Examples
--------------------------------

The following curl command will install the latest DCM Agent and configure it to communicate to this agentManager server: **wss://66.57.3.53/agentManager**. 
For most DCM Agent installs in On-Premise Dell Cloud Manager server environments that is the only required option. The DCM Agent will also be started after the install finishes. 

  :samp:`curl -k http://linux.stable.agent.enstratius.com/installer.sh | bash -s - -u wss://66.57.3.53/agentManager && service dcm-agent start`

  .. code-block:: text

      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed
      0     0    0     0    0     0      0      0 --:--:--  0:00:05 --:--:--     0rhel-6.6-x86_64
    100  9933  100  9933    0     0   1939      0  0:00:05  0:00:05 --:--:--  118k
    Starting the installation process...
    Downloading DCM Agent from https://linux.stable.agent.enstratius.com/dcm-agent-rhel-6.6-x86_64.rpm
    This may take a few minutes.
    Downloading https://linux.stable.agent.enstratius.com/dcm-agent-rhel-6.6-x86_64.rpm ...
    Installing DCM Agent.
    
    *** The remaining output from the install has been omitted in order to reduce clutter ***

  :download:`Click here to view the entire install output <files/noninteractive_install1_output.txt>`

The following curl command will install the latest DCM Agent, configure it for the OpenStack cloud, install the latest Chef client, and configure the DCM Agent to communicate to
this agentManager server: **wss://66.57.3.53/agentManager**. The DCM Agent will also be started after the install finishes.

  :samp:`curl -k http://linux.stable.agent.enstratius.com/installer.sh | bash -s - -c OpenStack --chef-client -u wss://66.57.3.53/agentManager && service dcm-agent start`

  .. code-block:: text

      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed
      0     0    0     0    0     0      0      0 --:--:--  0:00:05 --:--:--     0rhel-6.6-x86_64
    100  9933  100  9933    0     0   1952      0  0:00:05  0:00:05 --:--:--  183k
    Starting the installation process...
    Downloading DCM Agent from https://linux.stable.agent.enstratius.com/dcm-agent-rhel-6.6-x86_64.rpm
    This may take a few minutes.
    Downloading https://linux.stable.agent.enstratius.com/dcm-agent-rhel-6.6-x86_64.rpm ...
    Installing DCM Agent.

    *** The remaining output from the install has been omitted in order to reduce clutter ***

  :download:`Click here to view the entire install output <files/noninteractive_install2_output.txt>`
