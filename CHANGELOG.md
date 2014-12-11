# 0.9.8 (2014-12-11)

Features
* Upgraded the agent installer script to docker 1.3.2.
* Ubuntu distributions on EC2 can mount mount encrypted volumes.
* RAID mounts on Ubuntu distribution on EC2.
* Add a debug report utility so that users can more accurately
  report versions and deployments when they experience problems.

Bug Fixes
* A race condition in the jobrunner which could cause a mismatch of
  output was fixed.

# 0.9.7 (2014-12-04)

Features
* Install puppet client and DCM appropriate configuration when running
  configure_server with puppet.
* Enable mount but limit it to specific clouds and distributions.

Bug Fixes
* Decode unicode before sending log lines to DCM.
* Report errors from listDevices properly.

# 0.9.6 (2014-11-25)

Features
* Added module feature descriptors for handshake.
* Added auto-detection of platform.

Bug Fixes
* Loaded konami properly for testing support.

# 0.9.5 (2014-11-12)

Features
* Added RHEL with x86_64 and fedora as supported distributions.
* Added in initial agent support for docker.
* Added a means to guess the effective cloud that a VM is on.
* Added in support for OpenStack.
* Added script to install both the agent and docker.

Bug Fixes
* Added sudo and curl when needed in the installer script.
* Changing the default agent manager contact string and allowed
  for a default port in the url.
* Reconfiguring an agent if one was previously installed on the VM.

# 0.9.4 (2014-10-03)

Features
* Added docker plugins to allow the agent to control containers running
  via a local docker daemon.
* Enabled heartbeat from the agent to the agent manager to avoid timeouts
  from routers/firewalls/etc.
* Passed a list of available commands to the agent manager on handshake
  and thus bumped the protocol versions to 102.
* Added support module for commands that require paging.
* Improved testing code.
* Removed responses to stale lookups from the database.  This will be revisited
  in the future as the agent matures.
* Added paging support for commands with response greater than 16KB.
* Added support for CloudStack handshakes.
* Avoid the expensive "initialize" call when re-handshaking after the
  connection is dropped.
* Added a script to the archive for configuring the agent and docker from
  userdata (cloud-init style).
* Added in OpenStack meta-data allowing a successful handshake with servers
  launched on OpenStack clouds.

Bug Fixes:
* When installing if a user existed whose name contained the string "dcm"
  the install would fail.  This is now fixed.
* Repaired the install script so that the architecture can be forced as well.
* Fixed an error in the CloudStack handshake.

# 0.9.3 (2014-09-12)

Features:
* Added coverage reports for tests.
* Added vagrant tests in virtualbox to match ec2 tests.

Bug Fixes:
* Fixed a bug in type checker resulting in false successes.
* Error in installServer script fix by setting the absolute sudo path.
* Advanced to the new cacert.
* Allow the encryption key in mount to be optional.
* Fixed Azure handshake.
* Fixed GCE meta-data handshake.

# 0.9.2 (2014-08-22)

Features:
* Improved package management.
* Get DHCP address on distros that user dhcpcd.  This will allow such distros
  to work on Joyent.
* Refactored cloud meta data handling.
* Additional unit tests.
* Added auto upgrade script and confirmed upgrade behavior.

Bug Fixes:
* No longer setting the ownership of all temp files to root.
* Fixed occasional thread handler exceptions from SQLAlchemy.

# 0.9.1 (2014-08-05)

Features:
* An enhancements to the packaging system.
* Added the program dcm-agent-gen-docs to auto-generate protocol documentation
  from the source code.
* Additional tests added for failure cases of various system commands.

Bug Fixes:
* Fix issue that caused the agent to be restarted when a connection timed out.
* Verify that user names are limited to a safe character set.

Bug Fixes:

# 0.9.0 (2014-07-16)

Initial release
---------------

Features:
* A set of pluggable modules that are remotely executed via commands from DCM.
* Communicate with DCM via websockets.
* Mount and format volumes.
* Add and remove users.
* Rename hosts.
* Interaction with content management services (chef and puppet).

Know Issues:
* May require a restart after the websocket connection times out.
  https://enstratus.fogbugz.com/default.asp?4827
