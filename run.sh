#!/bin/bash
FLAGS=
MODE=$1
PORT="${2:-5000}"
IMAGE="${3:-mutnmt:latest}"

if [ $MODE = "cuda" ]
then
	FLAGS="--gpus all"
fi

echo "Running MutNMT (mode: $MODE) with FLAGS=$FLAGS and IMAGE=$IMAGE on port $PORT"

docker run \
$FLAGS \
-d \
--name mutnmt \
-p $PORT:5000 \
-v $(pwd)/app/preloaded:/opt/mutnmt/app/preloaded \
-v $(pwd)/data:/opt/mutnmt/data \
$IMAGE
