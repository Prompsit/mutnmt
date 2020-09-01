#!/bin/bash
FLAGS=
IMAGE=mutnmt:latest

if [ $1 = "cuda" ]
then
	FLAGS="--gpus device=2"
	#IMAGE=mutnmt:latest
fi

echo "Running MutNMT Docker with FLAGS=$FLAGS and IMAGE=$IMAGE"

docker run \
$FLAGS \
-d \
--name mutnmt \
-p 5000:5000 \
-v $(pwd)/app:/opt/mutnmt/app \
-v $(pwd)/data:/opt/mutnmt/data \
-e NVIDIA_VISIBLE_DEVICES=2 \
$IMAGE
