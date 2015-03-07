#!/bin/bash

cd `dirname $0`
start_dir=`pwd`

distro_to_build=$1

DCM_AGENT_EXTRAS_VERSION=`grep SEARCH_TOKEN omnibus-dcm-agent-extras/config/projects/dcm-agent-extras.rb  | awk '{ print $2 }' | sed 's/"//g'`
echo "Building version $DCM_AGENT_EXTRAS_VERSION for $distro_to_build"

if [ -z $DCM_AWS_EXTRAS_BUCKET ]; then
    echo "DCM_AWS_EXTRAS_BUCKET is not set"
    exit 1
fi
if [ -z $AWS_ACCESS_KEY ]; then
    echo "AWS_ACCESS_KEY is not set"
    exit 1
fi
if [ -z $AWS_SECRET_KEY ]; then
    echo "AWS_SECRET_KEY is not set"
    exit 1
fi

working_dir=`mktemp -d /tmp/dcmextrasbuilder.XXXXXX`

docker_envs="-e DCM_AGENT_EXTRAS_VERSION=$DCM_AGENT_EXTRAS_VERSION -e AWS_ACCESS_KEY=$AWS_ACCESS_KEY -e AWS_SECRET_KEY=$AWS_SECRET_KEY -e DCM_AWS_EXTRAS_BUCKET=$DCM_AWS_EXTRAS_BUCKET -e DCM_EXTRAS_FORCE_REBUILD=TRUE "
cp -r * $working_dir

cp $distro_to_build/Dockerfile $working_dir
docker build -t xtrabuilder$distro_to_build $working_dir
if [ $? -ne 0 ]; then
    echo "The docker build failed for $distro_to_build"
    rm -rf $working_dir
    exit 1
fi

dockername=`uuidgen`
docker run --name=$dockername $docker_envs xtrabuilder$distro_to_build /bin/build-upload.sh
if [ $? -ne 0 ]; then
    echo "The docker run failed for $distro_to_build"
    rm -rf $working_dir
    exit 1
fi
echo "Container ID is $dockername"
echo "$distro_to_build SUCCESS"
docker rm -f $dockername
rm -rf $working_dir
