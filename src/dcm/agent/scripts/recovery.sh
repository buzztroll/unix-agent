#!/bin/bash

start_dir=`pwd`
cd `dirname $0`
this_dir=`pwd`

function print_help() {
    echo "
Recover a DCM Agent recovery file.
----------------------------------

This script will decrypt (where necessary) a DCM Agent recovery file.  Once
complete a new tarball will exist and can be copied back into the server where
it was created.  They it should be untarred in the root directory of that
server.  This will restore all the files that where removed by the
dcm-agent-scrubber.

This script must be run on a file system that contains the private key which
corresponds to the public key used to encrypt it.  That public key can be found
at $this_dir/public_key.

Options: <destination tarball> [<path to private key>]
"
}

function handle_encrypted_rescue() {
    PRIVATE_KEY_LOCATION=$1
    if [ ! -f $PRIVATE_KEY_LOCATION ]; then
        echo "The private key $PRIVATE_KEY_LOCATION does not exist.  Please specify a path to the private key that can decrypt this file"
        exit 1
    fi

    which openssl > /dev/null
    if [ $? -ne 0 ]; then
        echo "The openssl CLI tool must be installed on your system and in your path."
        exit 1
    fi
    ENC_DATA_ENC=data.enc
    if [ ! -f $ENC_DATA_ENC ]; then
        echo "The encrypted data file cannot be found.  The file $ENC_DATA_ENC should be in the same directory as this script.  Please very that this is a proper rescue file."
        exit 1
    fi

    SYMM_KEY=`openssl rsautl -decrypt -inkey $PRIVATE_KEY_LOCATION -in key`
    openssl aes-256-cbc -d -in $ENC_DATA_ENC -out $RECOVERY_DESTINATION -k $SYMM_KEY
    if [ $? -ne 0 ]; then
        echo "Failed to decrypt the data file.  Please verify that this is the private key $PRIVATE_KEY_LOCATION is the correct key."
        exit 1
    fi
    return 0
}

function handle_nonencrypted_rescue() {
    ENC_DATA_ENC=data.enc
    if [ ! -f $ENC_DATA_ENC ]; then
        echo "The data file cannot be found.  The file $ENC_DATA_ENC should be in the same directory as this script.  Please very that this is a proper rescue file."
        exit 1
    fi

    set -e
    cp $ENC_DATA_ENC $RECOVERY_DESTINATION
    set +e
    return 0
}

if [ "X$1" == "--help" ] || [ "X$1" == "-h" ]; then
    print_help
    echo 0
fi

RECOVERY_DESTINATION=$1
if [ -z $RECOVERY_DESTINATION ]; then
    print_help
    echo "You must pass in a recovery destination"
    exit 1
fi

PRIVATE_KEY=~/.ssh/id_rsa
if [ ! -z $2 ]; then
    PRIVATE_KEY=$2
fi

if [ ! -e key ]; then
    echo "No key file found.  This rescue file must not have been encrypted."
    echo "Please consider encrypting it in the future"
    handle_nonencrypted_rescue
else
    handle_encrypted_rescue $PRIVATE_KEY
fi

echo "The recovery tarball can be found at: $RECOVERY_DESTINATION"
echo "To complete the recovery process copy this file to the server where it was created and untar it in the root directory"

exit 0
