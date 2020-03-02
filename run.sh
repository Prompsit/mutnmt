#!/bin/bash
FLAGS=
IMAGE=mutnmt:latest

if [ $1 = "cuda" ]
then
	FLAGS="--gpus all"
	#IMAGE=mutnmt:latest
fi

echo "Running MutNMT Docker with FLAGS=$FLAGS and IMAGE=$IMAGE"

docker run \
$FLAGS \
-d \
--name mutnmt \
-p 5000:5000 \
-v /home/prompsit/mutnmt2/app:/opt/mutnmt/app \
$IMAGE \
tail -f /dev/null
