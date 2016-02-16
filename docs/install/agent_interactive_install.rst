.. raw:: latex
  
      \newpage

.. _agent_interactive_install:

Interactive Install Example
---------------------------

Run the following command below with **root** authority to install the DCM Agent in interactive mode.

  :samp:`bash <( curl -k -L https://linux-stable-agent.enstratius.com/installer.sh )`

  .. code-block:: text
    :emphasize-lines: 19,21,35-36,45

    root@ip-10-29-59-177:~# bash <( curl -k -L https://linux-stable-agent.enstratius.com/installer.sh )

    *** some display output from the install has been omitted in order to reduce clutter ***

    The detected cloud is UNKNOWN
     0) Amazon
     1) Azure
     2) CloudStack
     3) CloudStack3
     4) DigitalOcean
     5) Google
     6) Joyent
     7) OpenStack
     8) Other
     9) ScaleMatrix
    10) UNKNOWN
    11) VMware
    12) VirtuStream
    13) WindowsAzurePack
    Select your cloud (UNKNOWN): 0
    Please enter the contact string of the agent manager (wss://dcm.enstratius.com/agentManager)

    Would you like to disable certificate checking? (not recommended) (y/N)
    y
    ...Done.
    Changing ownership to dcm:dcm
    Would you like to start the agent on boot? (Y/n)
    Y
     Adding system startup for /etc/init.d/dcm-agent ...
       /etc/rc0.d/K20dcm-agent -> ../init.d/dcm-agent
       /etc/rc1.d/K20dcm-agent -> ../init.d/dcm-agent
       /etc/rc6.d/K20dcm-agent -> ../init.d/dcm-agent
       /etc/rc2.d/S20dcm-agent -> ../init.d/dcm-agent
       /etc/rc3.d/S20dcm-agent -> ../init.d/dcm-agent
       /etc/rc4.d/S20dcm-agent -> ../init.d/dcm-agent
       /etc/rc5.d/S20dcm-agent -> ../init.d/dcm-agent
    Using AWS
    (Optional) Would you like to install chef client? (Y/N) Y
    Enter the chef-client version you would like to install or press ENTER for 11.16.4
    12.6
    Installing chef-client version 12.6.
    curl -L http://www.opscode.com/chef/install.sh | sudo bash -s -- -v 12.6
    To start the agent now please run:
    /etc/init.d/dcm-agent start
    root@ip-10-29-59-177:~#
