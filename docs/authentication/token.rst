.. _token:

Agent Token
============

The handshake process provides DCM with a safe way to know that it is talking
to an agent on the correct server, however DCM also needs to know that it is
talking to a trusted user on the server and not some bad actor spoofing the
agent.

When DCM launches servers with agents it will often create additional users
on those servers.  Sometimes the users are trusted with administrative access
and sometimes they are not.

The DCM UNIX agent is a publicly available open source project, thus it would
be very easy for a nonroot user to install a copy of it into their account and
connect to DCM posing as the root user.  In this case the *handshake* would
most likely be successful because the bad actor would but running on the
trusted server.  Because sensitive information flows between DCM and the agent
we must make sure that a bad actor cannot authenticate with DCM in this way.

Protocol 104
------------

To protect against this case, when the agent first starts it generates a random
string called a *token*.  This token is persisted in a file that can only be
read by the root account.  When the agent connects to a DCM it presents this
token.  If the handshake process is successful, and this is the first time that
the agent has ever connected, then DCM accepts this token an associates it with
this server's agent.  All future connections from the same server must present
the exact same token.  If they fail to do so the handshake is rejected.

When an image is first booted it is assumed that it is secure.  If it has
previously been compromised there is little DCM can do to protect against any
bad actors on it.  DCM ensures that only users with access to the account which
first authenticated can authenticate in the future.  This specifically prevents
any new accounts created by DCM from spoofing an agent on the server.

Stale Tokens
------------

The token file should be considered a secret.  However its scope is limited to
one specific server running in a cloud.  Once that server is terminated the
token is no longer relevant.  Even while the server is still running the token
is not valuable to any other server.

The handshake protocol makes sure that DCM is talking to the right server, and
the presentation of the token makes sure that DCM is talking to the right
user account on that server.  If one server obtains access to another servers
token it does not compromise the first server.

This is an important point to consider when making images from instances.  DCM
has a very convenient feature that allows a customer to take a snapshot of a
currently running instance and save it to a new image which can then be booted
many times.  When creating such an image it is very important that the parent
instance is scrubbed of any potential secrets.  It is strongly recommended that
the token file is not burnt into child images, however if this does happen all
is not lost.

Token Regeneration
------------------

When an agent first connects and presents a token DCM checks to see if that
token is in use by another server.  If it is the that agent will be instructed
to regenerate a new token and try again.  In this way DCM and the agent can
detect stale tokens while the server instance is still trusted.


