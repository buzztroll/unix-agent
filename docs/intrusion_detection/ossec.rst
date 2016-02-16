.. _ossec:

Ossec Intrusion Detection
=========================

The agent supports running `Ossec <http://ossec.github.io/>`_.  To do so you can run the installer or configure
programs with the following options:

    --instrusion-detection-ossec, -d Flag to install and start ossec.  In addition the agent will process alerts.
                                     Default is False

    --ids-alert-threshold, -T      Integer alert level at which the agent will persist locally but not log back to DCM.
                                   The default is 5.

This will run the **installOssec** script and start the ossec daemon.  In addition it will start the ossec alert routine
which will check the ossec alert log and persist any alerts that meet the threshold to the agent database.
In addition, any alerts that are level 10 or above will be displayed on the DCM console UI.
If you wish to stop using ossec on a given VM, simply stop all ossec services, and reconfigure the agent by opening
`/dcm/etc/agent.conf` and set `ossec=False`.  Upon restart the agent will not start the
ossec services.
