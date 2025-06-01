#!/bin/bash

IMAGE_NAME="recipe-scraper:latest"

echo "Building Docker image $IMAGE_NAME ..."

docker build -t $IMAGE_NAME .

if [ $? -eq 0 ]; then
  echo "Docker image built successfully."
else
  echo "Docker build failed!" >&2
  exit 1
fi
