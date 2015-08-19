Agent Architecture
==================

While the full internal workings of the dcm-agent and its interactions with
Dell Cloud Manager is outside of the scope of this document, some details are
provided here to assist the user in understanding how to run it.

The dcm-agent is a multi-threaded python program that runs inside of a VM which
was launched by DCM.  A connection is formed from the dcm agent to DCM over
which instructions from DCM flow.  The instructions cause the agent to run
system changing commands which allow DCM to coordinate and control cloud
applications.

Web Sockets
-----------

The agent connects to DCM using web sockets. The connection direction is always
out, so no in-bound ports need to be opened up on your server and it is
NAT-friendly. When the agent starts it creates a thread of execution which
periodically attempts to form a connection with DCM.

Once the connection is formed, commands can be received from DCM and executed
by the agent. The agent can also respond to completed commands and can also log
information back to DCM.

If a web socket connection is lost, the agent will periodically attempt to
re-connect. This is a normal part of the agent's execution. Web socket
connections will time out from being idle, or DCM may close them, or a network
partition may happen. The agent is tolerant of all such situations.
