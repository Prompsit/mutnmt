from app.models import Engine
from app import db, app

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
    def launch(user_id, id):
        engine = Engine.query.filter_by(id=id).first()
    
        Trainer.running_joey[user_id] = subprocess.Popen(["python3", "-m", "joeynmt", "train", 
                                            os.path.join(engine.path, "config.yaml"), 
                                            "--save_attention"], cwd=app.config['JOEYNMT_FOLDER'])

        threading.Thread(target=Trainer.monitor, args=[id]).start()

        engine.status = "training"
        db.session.commit()

    @staticmethod
    def monitor(id):
        engine = Engine.query.filter_by(id=id).first()
        while engine.status != "stopped":
            power = 0
            pynvml.nvmlInit()
            for i in range(0, pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                power = power + (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
            power = round(power / pynvml.nvmlDeviceGetCount())

            engine.power = int(power)
            db.session.commit()
                

    @staticmethod
    def finish(user_id, id):
        if user_id in Trainer.running_joey.keys():
            Trainer.running_joey[user_id].kill()
            del Trainer.running_joey[user_id]

    @staticmethod
    def stop(user_id, id):    
        Trainer.finish(user_id, id)

        engine = Engine.query.filter_by(id = id).first()
        engine.status = "stopped"
        engine.finished = datetime.datetime.utcnow().replace(tzinfo=None)
        db.session.commit()