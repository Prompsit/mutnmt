from app.models import Engine
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

import os
import glob

class TensorUtils(object):
    def __init__(self, engine_id):
        self.eacc = None
        
        engine = Engine.query.filter_by(id = engine_id).first()
        if engine.model_path:
            tensor_path = os.path.join(engine.model_path, "tensorboard")
        else:
            tensor_path = os.path.join(engine.path, "model/tensorboard")
        files = glob.glob(os.path.join(tensor_path, "*"))
        
        if len(files) > 0:
            log = files[0]

            self.eacc = EventAccumulator(log)
            self.eacc.Reload()

    def is_loaded(self):
        return self.eacc is not None

    def get_tag(self, tag):
        if self.eacc:
            tags = self.eacc.Tags()
            if tag in tags.get('scalars'):
                return self.eacc.Scalars(tag)

        return []

