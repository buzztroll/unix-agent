Authenticating and Authorizing Connections
==========================================

The agent is a process that runs with root access inside of a server.  It
connects to DCM and takes instructions from DCM that run system changing
commands.  These commands do things like add additional users that also have
root level access.  Because of this it is crucial that this connection is
safely formed and that both sides of the connection are assured they are
in communication with the trusted and expected part.

When the agent connects to DCM it need to be assured that there is no bad
actor spoofing the expected DCM server and that there is no man in the middle.
How this is achieved is discussed here :ref:`agent_trust`.

DCM must also decide if the agent that connected is safe in the following ways:
 - It is running on the server it claims to be.  This is discussed
   here: :ref:`handshake`.
 - It is talking to a trusted user on that server.  This is discussed
   here :ref:`token`.