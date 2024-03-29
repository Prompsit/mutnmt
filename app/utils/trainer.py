from app.models import Engine
from app import db, app
from app.utils.power import PowerUtils
from app.utils import tasks
from app.utils.GPUManager import GPUManager
from celery.task.control import revoke

import datetime
import logging
import sys
import os
import subprocess
import pynvml
import threading

class Trainer(object):
    running_joey = {}

    @staticmethod
    def launch(id, is_admin):
        task = tasks.train_engine.apply_async(args=[id, is_admin])
        monitor_task = tasks.monitor_training.apply_async(args=[id])
        return task.id, monitor_task.id

    @staticmethod
    def finish(engine):
        if engine.bg_task_id is not None:
            revoke(engine.bg_task_id, terminate=True)
            engine.bg_task_id = None
        
        if engine.pid is not None:
            executioner = subprocess.Popen("kill -9 {}".format(engine.pid), shell=True)
            engine.pid = None

        if engine.gid is not None:
            GPUManager.free_device(engine.gid)
            engine.gid = None

        db.session.commit()

    @staticmethod
    def stop(id, user_stop=False, admin_stop=False):
        engine = Engine.query.filter_by(id = id).first()
        Trainer.finish(engine)

        engine.status = "stopped" if user_stop else "stopped_admin" if admin_stop else "finished"
        engine.finished = datetime.datetime.utcnow().replace(tzinfo=None)
        
        # Save engine runtime
        launched = datetime.datetime.timestamp(engine.launched)
        finished = datetime.datetime.timestamp(engine.finished) if engine.finished else None
        elapsed = (finished - launched) + (engine.runtime if engine.runtime else 0)
        engine.runtime = elapsed

        db.session.commit()
