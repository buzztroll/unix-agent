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
remains, a bad actor could read secret information from it.  To solve this
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

The recovery file is a gziped tarball with the following format:
- recovery.sh
  A script which aids in the recovery process
- data.enc
  The data removed from the system by the scrubber in a tarball.  If encryption
  was used to create this it will be an encrypted file.
- public_key
  The public key used to encrypt the symmetric key used to encrypt data.enc.
  If encryption was not used this file will not exist.
- key
  The encrypted symmetric key used to encrypt data.enc.  This file must be
  decrypted by the private key which matches the public key used to create it.
  The decrypted result can then be used to decrypt the data.enc and thereby
  recover the data.  If encryption was not used this file will not exist.

To recover the scrubbed data untar the recovery file and run the recovery.sh
file.  This will do all of the decryption work needed and will result in an
unencrypted tarball.  That tarball can then be copied to the server and untarred
in the root directory.

To recover all the deleted files run the following command from the system
that contains your private key:

