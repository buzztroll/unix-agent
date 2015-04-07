# 0.9.16 (2015-4-7)

Features:
* Audited the logs that are sent back to DCM for clarity.
* Including boot and cloud-init logs in the report tarball.
* Added support for konami to set the docker host.

Bug Fixes:
* pep8 cleanup
* Delete the pid file when the agent is shutdown to avoid mistaken pid
  conflict on startup.
* Properly report idle time in system statistic reporter.

# 0.9.15 (2015-4-2)

Features:
* Support for RHEL 7
* Detect and reconfigure an existing agent when trying to install a new
  agent.  This will help prevent the case of having multiple agents
  running.
* Send the log level when sending logs back to DCM.
* Auto-detect Azure based on the existence of "/var/lib/waagent/ovf-env.xml"

# 0.9.14 (2015-3-31)

Features:
* Added CentOS 7.0 packages.
* Added major version only installation to the installer.  This allows
  for example Debian 7.8 to find and install Debian 7.7 packages.
* Throw a nicer error when a bad hostname is passed to rename.
* No longer alter the hostname passed to rename.

Bug Fixes:
* Fixed version detection for RHEL/CentOS.
* User insserv for starting on boot on debian systems.

# 0.9.13 (2015-3-25)

Features:
* Report an error if sudo is not found on the system.
* Added daemon logging to the init.d script.
* Added a flag to install chef-client with the agent installation.
* Added help to the installer script.
* Added support for DCM konami instances.
* Added an omnibus builder for soft dependencies.  Currently puppet is
  the only package needed.
* Added switches to the installer to download and install the extras
  packages.
* Added additional logging.
* Upgraded to SQLite 3.8
* Upgraded builder to omnibus 4.0

Bug Fixes
* Updated the certs package for curl.
* Fixed a bug prevent chef from running on RHEL
* Cleared the environment before running the agent.  This eliminated a
  problem when starting the agent with proxy variables set.
* Fixed a bug in the test suite that caused occasional "read-only DB"
  error.

# 0.9.12 (2015-1-25)

Features:
* Added a path to the agents python interpreter to the environment variable
  DCM_PYTHON in the environment in which all scripts are run.
* Added the fetch_run plug-in.  This will download a executable from a
  repository (currently just http:// and file:// are supported) and run
  it locally.
* Added support to run python scripts with the agents python interpreter
  directly.

Bug Fixes
* Fixed a problem where Joyent could not be auto-detected.
* On certain cloud and distribution combinations an agent may start before
  the meta-data server is ready.  This results in an "instance ID" of
  None and thus a failed handshake.  To fix this we get the handshake
  document with every connection attempt instead of just once at the
  beginning.  This bug occurred most often on images with "burnt-in"
  agents.

# 0.9.11 (2014-1-6)

Features:
* Support for RAID levels in addition to RAID0

Bug Fixes
* Locking in the chef version which fixes configuration management on
  ubuntu 14.04 i386.

# 0.9.10 (2014-12-19)

Bug Fixes
* Add pluginsync=true to the puppet configuration.  This fixes puppet
  on various Ubuntu 32 bit distributions.

# 0.9.9 (2014-12-17)

Features
* Removed legacy support for services and various other things that
  are not needed in the new agent.
* Removed SQL Alchemy and replaced with direct SQLite support.
* Removed references to clouds that are not yet fully supported.
* Upgrade to python 2.7.8
* pep8 cleanup of the source code.
* Do not mount if the mount point is not empty.

Bug Fixes
* Allowed default mount point to work.

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
