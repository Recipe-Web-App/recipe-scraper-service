#!/bin/bash

IMAGE_NAME="recipe-scraper:latest"
CONTAINER_NAME="recipe-scraper-dev"
HOST_PORT=8000
CONTAINER_PORT=8000

docker rm -f $CONTAINER_NAME 2>/dev/null

docker run --rm -it \
  -p $HOST_PORT:$CONTAINER_PORT \
  $CODE_MOUNT \
  --name $CONTAINER_NAME \
  $IMAGE_NAME
