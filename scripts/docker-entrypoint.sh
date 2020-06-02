#!/bin/bash
PORT=5000
ROOT=/opt/mutnmt

cd $ROOT
source venv/bin/activate

redis-server conf/redis.conf

nohup celery worker --workdir $ROOT \
                    -A app.utils.tasks.celery --loglevel=info \
                    --logfile=$ROOT/data/logs/celery-worker.log &

if [ -z "$DEBUG" ] || [ "$DEBUG" == "0" ]
then
    gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile $ROOT/data/logs/gunicorn.log --error-logfile $ROOT/data/logs/gunicorn-error.log app:app
else
    FLASK_DEBUG=1 FLASK_ENV=development flask run --host 0.0.0.0 --port $PORT
fi

tail -f /dev/null