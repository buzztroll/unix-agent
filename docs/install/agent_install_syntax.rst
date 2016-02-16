.. raw:: latex
  
      \newpage

.. _agent_installation_syntax:

Interactive install syntax
--------------------------

  Issue the following command to install the DCM Agent in "interactive mode".

    :samp:`bash <( curl -k -L https://linux-stable-agent.enstratius.com/installer.sh )`

  You will be prompted for:

  1. Cloud provider of the launched server where the DCM Agent will be
     installed.
  2. Web socket URL string for the Dell Cloud Manager provisioning server
     agentManager service.

    Format: wss://\ **hostname_or_ipaddress**\/agentManager

  3. Whether or not to start the DCM Agent at system boot (default is No)
  4. Whether or not to install the latest Chef client (default is No)
  5. The version of Chef client to install (default is 11.16.4)

  You can see an example of an interative installation :ref:`here.<agent_interactive_install>`
 
Non-interactive install syntax
------------------------------

  Issue the following command to install the DCM Agent in "non-interactive mode".

    :samp:`curl -k -L https://linux-stable-agent.enstratius.com/installer.sh | bash -s - [options]`

    .. code-block:: text

      Options: 


      --cloud {Amazon, etc...}, -c {Amazon, etc...}
                            The cloud where this virtual machine will be run.
                            Options: Amazon, Azure, CloudStack, CloudStack3,
                            Eucalyptus, Google, Joyent, OpenStack, Other, UNKNOWN

      --url URL, -u URL     The location of the dcm web socket listener

      --verbose, -v         Increase the amount of output produced by the script.

      --base-path BASE_PATH, -p BASE_PATH
                            The path to enstratius

      --mount-point MOUNT_PATH, -m MOUNT_PATH
                            The path to mount point

      --on-boot, -B         Setup the agent to start when the VM boots

      --reload-conf RELOAD, -r RELOAD
                            The previous config file that will be used to populate
                            defaults.

      --temp-path TEMP_PATH, -t TEMP_PATH
                            The temp path

      --user USER, -U USER  The system user that will run the agent.

      --connection-type CON_TYPE, -C CON_TYPE
                            The type of connection that will be formed with the
                            agent manager.

      --logfile LOGFILE, -l LOGFILE

      --loglevel LOGLEVEL, -L LOGLEVEL
                            The level of logging for the agent.

      --chef-client, -o Install chef client.

      --chef-client-version Version default is 11.16.4

      --install-extras      Install extras package

      --extra-package-location URL,  url of extra packages to be installed.  Default is https://linux-stable-agent.enstratius.com

      --instrusion-detection-ossec, -d Flag to install and start ossec.  In addition the agent will process alerts.  Default is False

      --ids-alert-threshold, -T      Integer alert level at which the agent will persist locally but not log back to DCM.


  You can see an example of an Non-interactive installation :ref:`here.<agent_noninteractive_install>`          

  .. note:: In most cases it is not necessary to specify the **-c** parameter as the DCM Agent can detect the cloud. 
  
  .. note:: By default the DCM Agent is configured to not be started at system boot.  If you wish to have the DCM Agent configured to be started at system boot then specify the **-B** or **--on-boot** option.

  .. note:: By passing the **--intrusion-detection-ossec** flag, the agent will download and install ossec, and will process alerts
            from it that are level 5 and above.  Any alerts below 10 are only stored in the agent database.  Any alerts
            10 or greater are sent to DCM and are displayed on the console.  To customize the level of alerts stored in the agent
            database simply pass your desired level to **--ids-alert-threshold** flag.

  .. warning:: The default value for the web socket URL is **wss://dcm.enstratius.com/agentManager** which is the Dell Cloud Manager SaaS provisioning server. This needs to be changed for On-Premise environments.
