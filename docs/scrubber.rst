Agent Image Scrubber
=====================================

DCM allows customers to create images from their current running image.  This
is a very helpful features that lets a customer configure a virtual machine
with the software and services that they need and then take a snapshot of the
instance for future use.  This powerful feature can also be dangerous.  If
the images are shared any private keys or other files that could include
secrets need to be deleted from the image before making it.  Further there can
be data caches that can confuse the image on reboot (dhcp leases and cloud-init
startup scripts for example).  These files should be removed as well.

The agent distribution comes with the program dcm-agent-scrubber.  This program
helps clean virtual machines in preparation for making an image from them.  For
a detailed list of options run:


    .. code-block:: text

      dcm-agent-scrubber --help

One important option is the *--rescue-tar*.  This option creates a tarfile that
will contain all of the deleted files.  This provides a way to recover any
crucial information that may be needed in the parent image.  This file should
then be copied off of the server before the image is created.