#!/bin/bash
PORT=5007
ROOT=/opt/mutnmt

mkdir -p /opt/mutnmt/data
mkdir -p /opt/mutnmt/data/redis-data
mkdir -p /opt/mutnmt/data/logs
mkdir -p /opt/mutnmt/data/tmp
mkdir -p /opt/mutnmt/data/userspace

cd $ROOT
source venv/bin/activate

redis-server conf/redis.conf

celery -A app.utils.tasks.celery --workdir $ROOT worker \
		--loglevel=info \
		--logfile=$ROOT/data/logs/celery-worker.log --detach

if [ -z "$DEBUG" ] || [ "$DEBUG" == "0" ]
then
    gunicorn -w 4 -b 0.0.0.0:5007 -k gevent --timeout 86400 --access-logfile $ROOT/data/logs/gunicorn.log --error-logfile $ROOT/data/logs/gunicorn-error.log app:app
else
    FLASK_DEBUG=1 FLASK_ENV=development flask run --host 0.0.0.0 --port $PORT
fi

tail -f /dev/null
