Agent Image Scrubber
=====================================

DCM allows customers to create images from their current running image.  This
is a very helpful features that lets a customer configure a virtual machine
with the software and services that they need and then take a snapshot of the
instance for future use.  This powerful feature can also be dangerous. Any
private keys or other files which include secrets that were on the system at
the time the image was made will be on the child image.  Anyone who then boots
the child image will have full root level access to all of the data on it and
thus access to any secrets left on that image.  Thus any such files need to be
removed before the image is created.  Further there can be data caches that
can confuse the image on reboot (dhcp leases and cloud-init
startup scripts for example).  These files should be removed as well.

The agent distribution comes with the program dcm-agent-scrubber.  This program
helps clean virtual machines in preparation for making an image from them.  For
a detailed list of options run:


    .. code-block:: text

      dcm-agent-scrubber --help

It is important to note that this program will delete files from the system on
which it is run.  Some of these files are needed for the system to function
properly (eg: /dcm/secure/token).  Because of this the scrubber includes a way
to safely create a recovery file.

The recovery file is a tarball that contains every file that was removed from
the system by the scrubber.  The system can be restored with this file by
untarring it in the root directory.

Of course if this recovery file is left on the created image the same problem
remains.  A bad actor could read secret information from it.  To solve this
problem the scrubber will encrypt the recovery file with the instance owners
RSA public key making it so only the original owner of the instance can access
the data in the recovery file.

note: It is still recommended that the recovery file be removed from the system
before making an image from it.

Scrubbing The Server
--------------------

Before making an image from a server that is already running the dcm agent we
recommend running the scrubber in the following way:

    .. code-block:: text

      dcm-agent-scrubber -k -A -H -t -r /tmp/dcm_scrubber_backup.tar.gz -e <path to your ssh public key>

Then copy the file */tmp/dcm_scrubber_backup.tar.gz.<ssh key name>* off of the
server and remove it from the server.

Recovery
--------

To recover all the deleted files run the following command from the system
that contains your private key:

