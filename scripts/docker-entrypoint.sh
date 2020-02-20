#!/bin/bash
PORT=5000

cd /opt/mutnmt
source venv/bin/activate

if [ -z "$DEBUG" ] && [ "$DEBUG" == "1" ]
then
    flask run --host 0.0.0.0 --port $PORT
else
    FLASK_DEBUG=1 FLASK_ENV=development flask run --host 0.0.0.0 --port $PORT
fi