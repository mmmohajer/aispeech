#!/bin/sh
docker container rm -f $(docker container ls -a -q)
docker image rm -f $(docker image ls -q)
# docker volume rm $(docker volume ls -q)
docker-compose -f ../../docker-compose-prod.yml up --build -d