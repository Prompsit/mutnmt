from app.models import Engine
from app import db, app
from toolwrapper import ToolWrapper

import datetime
import logging
import sys
import os

class Trainer(object):
    running_joey = {}

    @staticmethod
    def launch(user_id, id):
        engine = Engine.query.filter_by(id=id).first()
    
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        root.addHandler(handler)

        Trainer.running_joey[user_id] = ToolWrapper(["python3", "-m", "joeynmt", "train", os.path.join(engine.path, "config.yaml"), 
                                            "--save_attention"], cwd=app.config['JOEYNMT_FOLDER'])

        engine.status = "training"
        db.session.commit()

    @staticmethod
    def finish(user_id, id):
        print(Trainer.running_joey, file=sys.stderr)
        if user_id in Trainer.running_joey.keys():
            Trainer.running_joey[user_id].close()
            del Trainer.running_joey[user_id]

    @staticmethod
    def stop(user_id, id):    
        Trainer.finish(user_id, id)

        engine = Engine.query.filter_by(id = id).first()
        engine.status = "stopped"
        engine.finished = datetime.datetime.utcnow().replace(tzinfo=None)
        db.session.commit()