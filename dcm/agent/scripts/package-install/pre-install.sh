#!/usr/bin/env bash
# Copyright 2010-2013 Enstratius, Inc.
#
# pre-install - Set privileges of directories and files, make init scripts, run enstratius service.
# 
# This software is part of the Enstratius Cloud Management System. Only 
# authorized licensees of Enstratius may use this software and only
# in the context of Enstratius-managed virtual servers and machine images. 
# Unauthorized copying or distribution of this software is strictly prohibited.
# Authorized licensees may copy this software onto any machine images
# and/or virtual hosts being managed by the Enstratius system as needed.

set -u
PATH=/usr/sbin:/bin:${PATH}

# Create directory.
echo "Creating directory at /enstratus..."
if [ ! -d /enstratus ] ; then
	mkdir /enstratus
	if [ $? != 0 ] ; then
		echo "Could not create /enstratus directory. Are you running this as root?"
		exit 30
	fi
fi
echo "Done."

echo "Creating user and group..."
# Create enstratus group.
grep -q enstratus /etc/group
if [ $? != 0 ] ; then
	groupadd enstratus
	if [ $? != 0 ] ; then
		echo "Failed to add enstratus group."
		exit 40
	fi
fi
# Create enstratus user.
grep -q enstratus /etc/passwd
if [ $? != 0 ] ; then
	useradd -d /enstratus/home -g enstratus -s /bin/false -m enstratus
	if [ $? != 0 ] ; then
		echo "Failed to add enstratus user."
		exit 41
	fi
fi
echo "Done."
