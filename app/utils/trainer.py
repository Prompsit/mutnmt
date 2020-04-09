from app.models import Engine
from app import db, app

import datetime
import logging
import sys
import os
import subprocess

class Trainer(object):
    running_joey = {}

    @staticmethod
    def launch(user_id, id):
        engine = Engine.query.filter_by(id=id).first()
    
        Trainer.running_joey[user_id] = subprocess.Popen(["python3", "-m", "joeynmt", "train", 
                                            os.path.join(engine.path, "config.yaml"), 
                                            "--save_attention"], cwd=app.config['JOEYNMT_FOLDER'])

        engine.status = "training"
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