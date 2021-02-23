from app import app, db
from app.flash import Flash
from app.models import LibraryCorpora, LibraryEngine, Engine, File, Corpus_Engine, Corpus, User, Corpus_File, Language
from app.utils import user_utils, utils, data_utils, tensor_utils, tasks, training_log
from app.utils.trainer import Trainer
from app.utils.power import PowerUtils
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required
from sqlalchemy import func
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import namegenerator
import datetime
from werkzeug.datastructures import FileStorage
from celery.result import AsyncResult
from functools import reduce

import traceback
import hashlib
import os
import yaml
import shutil
import sys
import ntpath
import subprocess
import glob
import re
import json

train_blueprint = Blueprint('train', __name__, template_folder='templates')

@train_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_index():
    if user_utils.is_normal(): return redirect(url_for('index'))

    currently_training = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("training")).all()

    if (len(currently_training) > 0):
        return redirect(url_for('train.train_console', id=currently_training[0].id))

    currently_launching = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("launching")).all()
                            
    if (len(currently_launching) > 0): 
        return redirect(url_for('train.train_launching', task_id=currently_launching[0].bg_task_id))

    random_name = namegenerator.gen()
    tryout = 0
    while len(Engine.query.filter_by(name = random_name).all()):
        random_name = namegenerator.gen()
        tryout += 1

        if tryout >= 5:
            random_name = ""
            break

    random_name = " ".join(random_name.split("-")[:2])

    library_corpora = user_utils.get_user_corpora().filter(LibraryCorpora.corpus.has(Corpus.type == "bilingual")).all()
    corpora = [c.corpus for c in library_corpora]
    languages = Language.query.all()

    return render_template('train.html.jinja2', page_name='train', page_title='Train',
                            corpora=corpora, random_name=random_name,
                            languages=languages)

@train_blueprint.route('/launching/<task_id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_launching(task_id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    return render_template('launching.html.jinja2', page_name='train', page_title='Launching training', task_id=task_id)

@train_blueprint.route('/start', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_start():
    if user_utils.is_normal(): return url_for('index')
    engine_path = os.path.join(user_utils.get_user_folder("engines"), utils.normname(user_utils.get_user().username, request.form['nameText']))
    task = tasks.launch_training.apply_async(args=[user_utils.get_uid(), engine_path, { i[0]: i[1] if i[0].endswith('[]') else i[1][0] for i in request.form.lists()}])

    return jsonify({ "result": 200, "launching_url": url_for('train.train_launching', task_id=task.id) })

@train_blueprint.route('/launch_status', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def launch_status():
    task_id = request.form.get('task_id')
    result = tasks.launch_training.AsyncResult(task_id)

    if result and result.status == "SUCCESS":
        engine_id = result.get()
        if engine_id != -1:
            return jsonify({ "result": 200, "engine_id": result.get() })
        else:
            return jsonify({ "result": -2 })
    else:
        return jsonify({ "result": -1 })

@train_blueprint.route('/launch', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_launch():
    id = request.form.get('engine_id')
    if user_utils.is_normal(): return url_for('index')

    task_id, monitor_task_id = Trainer.launch(id, user_utils.is_admin())

    return url_for('train.train_console', id=id)

@train_blueprint.route('/console/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_console(id):    
    engine = Engine.query.filter_by(id = id).first()
    config_file_path = os.path.join(os.path.realpath(os.path.join(app.config['PRELOADED_ENGINES_FOLDER'], engine.path)), 'config.yaml')
    config = None

    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
    except:
        pass

    launched = datetime.datetime.timestamp(engine.launched)
    finished = datetime.datetime.timestamp(engine.finished) if engine.finished else None

    corpora_raw = Corpus_Engine.query.filter_by(engine_id = engine.id, is_info = True).all()

    corpora = {}
    for corpus_entry in corpora_raw:
        if corpus_entry.phase in corpora:
            corpora[corpus_entry.phase].append((corpus_entry.corpus, utils.format_number(corpus_entry.selected_size, abbr=True)))
        else:
            corpora[corpus_entry.phase] = [(corpus_entry.corpus, utils.format_number(corpus_entry.selected_size, abbr=True))]

    return render_template("train_console.html.jinja2", page_name="train",
            engine=engine, config=config,
            launched = launched, finished = finished,
            elapsed = engine.runtime, corpora=corpora, elapsed_format=utils.seconds_to_timestring(engine.runtime) if engine.runtime else None)

@train_blueprint.route('/graph_data', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_graph():
    tags = request.form.getlist('tags[]')
    id = request.form.get('id')

    engine = Engine.query.filter_by(id=id).first()
    tensor = tensor_utils.TensorUtils(id)

    stats = {}
    for tag in tags:
        data = tensor.get_tag(tag)
        if data:
            stats[tag] = []
            data_len = len(data)
            data_breakpoint = 1000 if data_len >= 100 else 10 if data_len > 10 else 1
            for i, item in enumerate(data):
                if item.step % data_breakpoint == 0 or (i + 1) == data_len:
                    stats[tag].append({ "time": item.wall_time, "step": item.step, "value": item.value })
            
            # The first step contains the initial learning rate which is
            # normally way bigger than the next one and it makes the chart
            # look like a straight line
            if tag == "train/train_learning_rate":
                stats[tag] = stats[tag][1:]

    return jsonify({ "stopped": engine.has_stopped(), "stats": stats })

@train_blueprint.route('/train_status', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_status():
    id = request.form.get('id')

    engine = Engine.query.filter_by(id = id).first()
    tensor = tensor_utils.TensorUtils(id)
    
    if tensor.is_loaded():
        stats = {}

        epoch_no = 0
        for data in tensor.get_tag("train/epoch"):
            if data.value > epoch_no:
                epoch_no = data.value
        stats["epoch"] = epoch_no

        launched = datetime.datetime.timestamp(engine.launched)
        now = datetime.datetime.timestamp(datetime.datetime.now())
        power = engine.power if engine.power else 0
        power_reference = PowerUtils.get_reference_text(power, now - launched)
        power_wh = power * ((now - launched) / 3600)

        return jsonify({ "stopped": engine.has_stopped(), "stats": stats, "done": engine.bg_task_id is None,
                            "power": int(power_wh), "power_reference": power_reference, 
                            "test_task_id": engine.test_task_id, "test_score": engine.test_score })
    else:
        return jsonify({ "stats": [], "stopped": engine.has_stopped() })

@train_blueprint.route('/train_stats', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_stats():
    engine_id = request.form.get('id')
    engine = Engine.query.filter_by(id=engine_id).first()

    score = 0.0
    ppl = "—"
    tps = []
    
    try:
        with open(os.path.join(engine.path, "model/train.log"), 'r') as log_file:
            for line in log_file:
                groups = re.search(training_log.training_regex, line, flags=training_log.re_flags)
                if groups:
                    tps.append(float(groups[6]))
                else:
                    # It was not a training line, could be validation
                    groups = re.search(training_log.validation_regex, line, flags=training_log.re_flags)
                    if groups:
                        bleu_score = float(groups[6])
                        score = bleu_score if bleu_score > score else score
                        ppl = float(groups[8])
    except FileNotFoundError:
        pass

    if len(tps) > 0:
        tps_value = reduce(lambda a, b: a + b, tps)
        tps_value = round(tps_value / len(tps))
    else:
        tps_value = "—"
    
    time_elapsed = None
    if engine.runtime:
        time_elapsed = engine.runtime

        if time_elapsed:
            time_elapsed_format = utils.seconds_to_timestring(time_elapsed)
        else:
            time_elapsed_format = "—"
    else:
        time_elapsed_format = "—"

    data = {
        "time_elapsed": time_elapsed_format,
        "tps": tps_value,
        "score": score,
        "ppl": ppl,
    }

    config_file_path = os.path.join(engine.path, 'config.yaml')
    with open(config_file_path, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
        data["val_freq"] = config["training"]["validation_freq"] if "validation_freq" in config["training"] else None
        data["epochs"] = config["training"]["epochs"] if "epochs" in config["training"] else None
        data["patience"] = config["training"]["patience"] if "patience" in config["training"] else None 
        data["batch_size"] = config["training"]["batch_size"] if "batch_size" in config["training"] else None 
        data["beam_size"] = config["testing"]["beam_size"] if "beam_size" in config["testing"] else None

    data["vocab_size"] = utils.file_length(os.path.join(engine.path, 'train.vocab'))

    return jsonify({
        "result": 200, 
        "data": data
    })

@train_blueprint.route('/log', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_log():
    engine_id = request.form.get('engine_id')
    draw = request.form.get('draw')
    search = request.form.get('search[value]')
    start = int(request.form.get('start'))
    length = int(request.form.get('length'))
    order = int(request.form.get('order[0][column]'))
    dir = request.form.get('order[0][dir]')

    engine = Engine.query.filter_by(id = engine_id).first()
    if engine.model_path:
        train_log_path = os.path.join(engine.model_path, 'train.log')
    else:
        train_log_path = os.path.join(engine.path, 'model/train.log')

    rows = []
    try:
        with open(train_log_path, 'r') as train_log:
            training_regex = r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),\d+\s+Epoch\s+(\d+)\sStep:\s+(\d+)\s+Batch Loss:\s+(\d+.\d+)\s+Tokens per Sec:\s+(\d+),\s+Lr:\s+(\d+.\d+)$'
            re_flags = re.IGNORECASE | re.UNICODE
            for line in train_log:
                groups = re.search(training_regex, line.strip(), flags=re_flags)
                if groups:
                    date_string = groups[1]
                    time_string = groups[2]
                    epoch, step = groups[3], groups[4]
                    batch_loss, tps, lr = groups[5], groups[6], groups[7]

                    # date = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
                    rows.append([time_string, epoch, step, batch_loss, tps, lr])
    except FileNotFoundError:
        pass

    if order is not None:
        rows.sort(key=lambda row: row[order], reverse=(dir == "desc"))

    final_rows = rows

    if start is not None and length is not None:
        final_rows = rows[start:(start + length)]

    rows_filtered = []
    if search:
        for row in final_rows:
            found = False

            for col in row:
                if not found:
                    if search in col:
                        rows_filtered.append(row)
                        found = True

    return jsonify({
        "draw": int(draw) + 1,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows_filtered) if search else len(rows),
        "data": rows_filtered if search else final_rows
    })


@train_blueprint.route('/attention/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_attention(id):
    if user_utils.is_normal(): return send_file(os.path.join(app.config['BASE_CONFIG_FOLDER'], "attention.png"))

    engine = Engine.query.filter_by(id = id).first()
    files = glob.glob(os.path.join(engine.path, "*.att"))
    if len(files) > 0:
        return send_file(files[0])
    else:
        return send_file(os.path.join(app.config['BASE_CONFIG_FOLDER'], "attention.png"))


def _train_stop(id, user_stop):
    Trainer.stop(id, user_stop=user_stop)
    return redirect(url_for('train.train_console', id=id))

@train_blueprint.route('/stop/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_stop(id):
    if user_utils.is_normal(): return redirect(url_for('index'))
        
    return _train_stop(id, True)

@train_blueprint.route('/finish/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_finish(id):
    if user_utils.is_normal(): return redirect(url_for('index'))
        
    return _train_stop(id, False)

@train_blueprint.route('/resume/<engine_id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_resume(engine_id):
    engine = Engine.query.filter_by(id=engine_id).first()

    new_model_path = os.path.join(engine.path, 'model-{}'.format(utils.randomfilename(length=8)))
    while os.path.exists(new_model_path):
        new_model_path = os.path.join(engine.path, 'model-{}'.format(utils.randomfilename(length=8)))

    config_file_path = os.path.join(engine.path, 'config.yaml')

    config = None
    with open(config_file_path, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.FullLoader)
        current_model = config["training"]["model_dir"]
        config["training"]["model_dir"] = new_model_path

        current_model_ckpt = os.path.join(current_model, 'best.ckpt')
        if os.path.exists(current_model_ckpt):
            config["training"]["load_model"] = current_model_ckpt
    
    with open(config_file_path, 'w') as config_file:
        yaml.dump(config, config_file)

    engine.model_path = new_model_path
    engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)
    engine.finished = None
    db.session.commit()

    task_id, _ = Trainer.launch(engine_id, user_utils.is_admin())

    i = 0
    while engine.has_stopped() and i < 100:
        db.session.refresh(engine)
        i += 1

    return redirect(url_for('train.train_console', id=engine_id))

@train_blueprint.route('/test', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_test():
    if user_utils.is_normal(): return redirect(url_for('index'))

    engine_id = request.form.get('engine_id')
    task = tasks.test_training.apply_async(args=[engine_id])

    engine = Engine.query.filter_by(id=engine_id).first()
    engine.test_task_id = task.id
    db.session.commit()

    return task.id

@train_blueprint.route('/test_status', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_test_status():
    if user_utils.is_normal(): return redirect(url_for('index'))

    task_id = request.form.get('task_id')
    task_success, task_value = utils.get_task_result(tasks.test_training, task_id)
    if task_success is not None:
        if not task_success:
            return jsonify({ "result": -2 })
        return jsonify({ "result": 200, "test": task_value })
    else:
        return jsonify({ "result": -1 })
