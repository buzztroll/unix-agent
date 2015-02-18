#!/bin/bash

echo "Deleting all containers" 
docker kill $(docker ps -q)
docker rm $(docker ps -a -q)

docker stop $(docker ps -a -q) >& /dev/null
docker rm $(docker ps -a -q) >& /dev/null

echo "Deleting all images"
docker rmi $(docker images -a -q) >& /dev/null

echo "Remaining:"
docker ps -a
docker images
