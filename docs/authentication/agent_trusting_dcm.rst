.. _agent_trust:

How Agents Trust DCM
====================

DCM sends agent's system level commands that allow root level access to the
server on which it is running.  Because of this it is crucial that the
agent trusts it has connected to the trusted DCM server and not an impostor
or possible man-in-the-middle.

Known Certificates
------------------

The agent handles this by using the https protocol underneath the websocket
protocol (wss://).  If DCMs certificate was signed by a Certificate
Authority (CA) known to the server on which it is running, then a default
installation of the agent can validate the connection and be assured that it
is to a trusted entity.  In the SaaS version of DCM this is the case.

Unknown Certificates
--------------------

For some *on premise* installations of DCM the certificate DCM uses may not
be signed by a known CA or it may be a self signed certificate.  There are two
ways to configure agents to work in this case.

1. Trust unknown certifications
   The agent can be configured to trust all certificates without validating
   them.  This is not a recommended configuration as the agent has no real
   means of trusting the connection to DCM.  However, on trusted networks or
   for test environments this can can be a very practical way to get started.

   To configure the agent to trust all certificates pass the option *-Z* to
   the the installation script along with the other needed options described
   in the `installation section install/agent_installation`.

   Additionally the configuration file /dcm/etc/agent.conf can be edited to
   allow untrusted certifications.  Open the file and find the following stanza


    .. code-block:: text

      [connection]
      # A flag to disable DCM certificate verification. When disabled certificates will
      # be ignored. This is useful for testing but should otherwise be set to False.
      allow_unknown_certs=True

2. Distribute the certificate to the agent's host server.

   The safe way to handle this situation is to distribute the correct cacert
   onto the agent's server machine.  In this way the correct certificate will
   be verified at the time of each connection.  Safely getting the certificate
   of your DCM host is outside of the scope of this discussion.  One way
   to achieve this is to run the following command from a safe place on the
   network:

   .. code-block:: text

     openssl s_client -showcerts -connect <dcm hostname>:443 < /dev/null

   The output from the above command should then be placed in a file on the
   server that is running the agent.  Finally the agents configuration should
   be updated.  Open */dcm/etc/agent.conf* and edit the following:

   .. code-block:: text

     [connection]
     ...
     # A path to the location of the CA certificate tobe used when authenticating with
     # DCM.
     ca_cert=<path to the certificate file>

In both cases the agent must be restarted before the change will take effect.
