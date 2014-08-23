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
