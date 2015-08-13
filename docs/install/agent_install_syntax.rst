.. raw:: latex
  
      \newpage

.. _agent_installation_syntax:

Interactive install syntax
--------------------------

  Issue the following command to install the DCM Agent in "interactive mode".

    :samp:`bash <( curl -k http://es-pyagent.s3.amazonaws.com/installer.sh )`

  You will be prompted for:

  1. Cloud provider of the launched server where the DCM Agent will be installed.
  2. Web socket URL string for the Dell Cloud Manager provisioning server agentManager service.

    Format: wss://\ **hostname_or_ipaddress**\/agentManager

  3. Whether or not to start the DCM Agent at system boot (default is No)
  4. Whether or not to install the latest Chef client (default is No)

  You can see an example of an interative installation :ref:`here.<agent_interactive_install>`
 
Non-interactive install syntax
------------------------------

  Issue the following command to install the DCM Agent in "non-interactive mode".

    :samp:`curl -k http://es-pyagent.s3.amazonaws.com/installer.sh | bash -s - [options]`

    .. code-block:: text

      Options: 

          -c, --cloud           cloud Provider 
                                --------------------------------------------------------------
                                Amazon, Azure, Bluelock, CloudStack, CloudStack3,
                                Eucalyptus, Google, Joyent, Konami, OpenStack, Other, UNKNOWN

          -u, --url             Web socket URL of the Dell Cloud Manager provisioning server agent manager service
                                Format: wss://hostname_or_ipaddress/agentManager 
                                Default: wss://dcm.enstratius.com/agentManager                                    

          -B, --on-boot         Configure the DCM Agent to start at system boot (default is not to boot at restart)

          -m, --mount-point     Mount point where DCM stores data (default /mnt/dcmdata)

          -t, --tmp-path        Path to the temporary directory  (default /tmp)

          -U, --user            Linux user that the DCM Agent will run as (default dcm)
                                If you specify a different user then that user must already exist.

          -o, --chef-client     Install the latest Chef client                                     
        
          -p, --base-path       Base path where to install the agent (default /dcm) 

          -r, --reload-conf     Reload the configuration file (used to populate defaults)             

          -L, --loglevel        Log level for logging (ERROR, WARN, INFO, DEBUG)                          

          -l, --logfile         Name of the DCM Agent logfile (default agent.log)
 
          -v, --verbose         Increase the amount of output produced by the script

  You can see an example of an Non-interactive installation :ref:`here.<agent_noninteractive_install>`          

  .. note:: In most cases it is not necessary to specify the **-c** parameter as the DCM Agent can detect the cloud. 
  
  .. note:: By default the DCM Agent is configured to not be started at system boot.  If you wish to have the DCM Agent configured to be started at system boot then specify the **-B** or **--on-boot** option.

  .. warning:: The default value for the web socket URL is **wss://dcm.enstratius.com/agentManager** which is the Dell Cloud Manager SaaS provisioning server. This needs to be changed for On-Premise environments.
