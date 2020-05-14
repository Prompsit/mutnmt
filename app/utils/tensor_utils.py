from app.models import Engine
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

import os
import glob

def get_tag(engine_id, tag):
    engine = Engine.query.filter_by(id = engine_id).first()
    tensor_path = os.path.join(engine.path, "model/tensorboard")
    files = glob.glob(os.path.join(tensor_path, "*"))
    
    if len(files) > 0:
        log = files[0]

        eacc = EventAccumulator(log)
        eacc.Reload()

        tags = eacc.Tags()
        if tag in tags.get('scalars'):
            return eacc.Scalars(tag)
    
    return []