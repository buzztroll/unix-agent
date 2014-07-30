#!/bin/bash

## private ip address with port for remote debugger
ip_addr=$2
ip_addr+=":5678"

## path to creds file which is a text file with entries like
## 1 <aws key> <aws secret> us_west_oregon
## where 1 signifies AWS as the provider.
## see es-ex-pyagent/src/dcm/agent/storagecloud.py for
## all current providers

creds_file=$(
python - <<EOF
import os
path_to_creds = os.path.split(os.path.abspath('testenv.sh'))[0] + '/creds'
print path_to_creds
EOF
)

if [ $1 = '-h' ] || [ $1 = '--help' ]
 then
     echo "
     ************************************************************************************
     usage:  source testenv.sh [option] [host private ip address]

     The options below let you determine which environment variables to
     set for testing the agent.  Note that to set DCM_AGENT_STORAGE_CREDS
     properly you must have your credentials in a file called creds in the
     same directory as this file. <whereeveryoursourceis>/es-ex-pyagent/tests/<here>
     Don't worry, there is a 'creds' entry in the .gitignore.  But please double check
     for yourself.

     Here are the possible options:
     -h/--help    show this help menu
     -a/--all     set DCM_AGENT_STORAGE_CREDS, PYDEVD_CONTACT, and SYSTEM_CHANGING_TEST
     -dp          set DCM_AGENT_STORAGE_CREDS, PYDEVD_CONTACT,
     -ds          set DCM_AGENT_STORAGE_CREDS, SYSTEM_CHANGING_TEST
     -ps          set PYDEVD_CONTACT, SYSTEM_CHANGING_TEST
     -dcm         set only DCM_AGENT_STORAGE_CREDS
     -pydev       set only PYDEVD_CONTACT
     -sct         set only SYSTEM_CHANGING_TEST
     ************************************************************************************"

elif [ $1 = '-a' ] || [ $1 = '--all' ]
 then
     export DCM_AGENT_STORAGE_CREDS=$creds_file
     export PYDEVD_CONTACT=$ip_addr
     export SYSTEM_CHANGING_TEST=1

elif [ $1 = '-dp' ]
 then
     export DCM_AGENT_STORAGE_CREDS=$creds_file
     export PYDEVD_CONTACT=$ip_addr
     unset SYSTEM_CHANGING_TEST

elif [ $1 = '-ds' ]
 then
     export DCM_AGENT_STORAGE_CREDS=$creds_file
     export SYSTEM_CHANGING_TEST=1
     unset PYDEVD_CONTACT

elif [ $1 = '-ps' ]
 then
     export PYDEVD_CONTACT=$ip_addr
     export SYSTEM_CHANGING_TEST=1
     unset DCM_AGENT_STORAGE_CREDS

elif [ $1 = '-dcm' ]
 then
     export DCM_AGENT_STORAGE_CREDS=$creds_file
     unset PYDEVD_CONTACT
     unset SYSTEM_CHANGING_TEST

elif [ $1 = '-pydev' ]
 then
     export PYDEVD_CONTACT=$ip_addr
     unset DCM_AGENT_STORAGE_CREDS
     unset SYSTEM_CHANGING_TEST

elif [ $1 = '-sct' ]
 then
     export SYSTEM_CHANGING_TEST=1
     unset DCM_AGENT_STORAGE_CREDS
     unset PYDEVD_CONTACT

else
 echo "
 *******************************************************************
 Unrecognized or absent argument please do: source testenv.sh --help
 *******************************************************************"

fi
