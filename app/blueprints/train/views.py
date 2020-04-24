from app import app, db
from app.models import LibraryCorpora, LibraryEngine, Engine, File, Corpus_Engine, Corpus, User
from app.utils import user_utils, utils
from app.utils.trainer import Trainer
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required
from sqlalchemy import func
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import namegenerator
import datetime

import hashlib
import os
import yaml
import shutil
import sys
import ntpath
import subprocess
import glob
import pynvml
import re

train_blueprint = Blueprint('train', __name__, template_folder='templates')

@train_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_index():
    if user_utils.is_normal(): return redirect(url_for('index'))

    currently_training = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("training")).all()

    if (len(currently_training) > 0):
        return redirect(url_for('train.train_console', id=currently_training[0].id))

    random_name = namegenerator.gen()
    tryout = 0
    while len(Engine.query.filter_by(name = random_name).all()):
        random_name = namegenerator.gen()
        tryout += 1

        if tryout >= 5:
            random_name = ""
            break

    random_name = " ".join(random_name.split("-")[:2])

    pynvml.nvmlInit()
    gpus = list(range(0, pynvml.nvmlDeviceGetCount()))
    corpora = Corpus.query.filter_by(owner_id = user_utils.get_uid()).all()
    return render_template('train.html.jinja2', page_name='train', 
                            corpora=corpora, random_name=random_name,
                            gpus=gpus)

@train_blueprint.route('/start', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_start():
    if user_utils.is_normal(): return redirect(url_for('index'))

    uengines_path = user_utils.get_user_folder("engines")
    blake = hashlib.blake2b()
    blake.update('{}{}'.format(user_utils.get_user().username, request.form['nameText']).encode("utf-8"))
    name_footprint = blake.hexdigest()[:16]

    engine_path = os.path.join(uengines_path, name_footprint)

    train_corpus = Corpus.query.filter_by(id = request.form['train_corpus']).first()
    dev_corpus = Corpus.query.filter_by(id = request.form['dev_corpus']).first()
    test_corpus = Corpus.query.filter_by(id = request.form['test_corpus']).first()

    engine = Engine(path = engine_path)
    engine.name = request.form['nameText']
    engine.source = train_corpus.source
    engine.target = train_corpus.target

    engine.corpora_engines.append(Corpus_Engine(corpus=train_corpus, engine=engine, phase="train"))
    engine.corpora_engines.append(Corpus_Engine(corpus=dev_corpus, engine=engine, phase="dev"))
    engine.corpora_engines.append(Corpus_Engine(corpus=test_corpus, engine=engine, phase="test"))

    engine.status = "training_pending"
    engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)
    engine.uploader_id = user_utils.get_uid()

    user = User.query.filter_by(id = user_utils.get_uid()).first()
    user.user_engines.append(LibraryEngine(engine=engine, user=user))

    try:
        os.mkdir(engine_path)
    except:
        return ""

    config_file_path = os.path.join(engine.path, 'config.yaml')

    shutil.copyfile(os.path.join(app.config['BASE_CONFIG_FOLDER'], 'transformer.yaml'), config_file_path)

    db.session.add(engine)
    db.session.commit()

    # Engine configuration
    Trainer.finish(user_utils.get_uid, id)

    config = None
    print(config_file_path, file=sys.stderr)

    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
    except:
        pass

    def link_files(corpus, phase):
        for file_entry in corpus.corpus_files:
            tok_path = '{}.mut.spe'.format(file_entry.file.path)
            tok_name = phase

            os.link(tok_path, os.path.join(engine.path, '{}.{}'.format(tok_name, 
                    config["data"]["src" if file_entry.role == "source" else "trg"])))

            config["data"][phase] = os.path.join(engine.path, tok_name)
            config["training"]["model_dir"] = os.path.join(engine.path, "model")

    corpus_train = Corpus_Engine.query.filter_by(engine_id = engine.id, phase="train").first().corpus
    link_files(corpus_train, "train")

    corpus_dev = Corpus_Engine.query.filter_by(engine_id = engine.id, phase="dev").first().corpus
    link_files(corpus_dev, "dev")

    corpus_test = Corpus_Engine.query.filter_by(engine_id = engine.id, phase="test").first().corpus
    link_files(corpus_test, "test")

    # Get vocabulary
    vocabulary_path = os.path.join(app.config['FILES_FOLDER'], 'mut.{}.vocab'.format(corpus_train.id))
    final_vocabulary_path = os.path.join(engine.path, "train.vocab")

    extract_vocabulary = subprocess.Popen("cat {} | head -n {} > {}".format(vocabulary_path, request.form['vocabularySize'], final_vocabulary_path),
                            shell=True)

    extract_vocabulary.wait()

    config["data"]["src_vocab"] = final_vocabulary_path
    config["data"]["trg_vocab"] = final_vocabulary_path

    config["name"] = engine.name
    config["training"]["epochs"] = int(request.form['epochsText'])
    config["training"]["patience"] = int(request.form['patienceTxt'])
    config["training"]["batch_size"] = int(request.form['batchSizeTxt'])

    with open(config_file_path, 'w') as config_file:
        yaml.dump(config, config_file)

    return redirect(url_for('train.train_launch', id=engine.id))

@train_blueprint.route('/launch/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_launch(id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    Trainer.launch(user_utils.get_uid(), id)

    return redirect(url_for('train.train_console', id=id))

@train_blueprint.route('/console/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_console(id):
    if user_utils.is_normal(): return redirect(url_for('index'))
    
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
    elapsed = (finished - launched) if engine.finished else None

    return render_template("train_console.html.jinja2", page_name="train",
            engine=engine, config=config,
            launched = launched, finished = finished,
            elapsed = elapsed)

@train_blueprint.route('/graph_data', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_graph():
    if user_utils.is_normal(): return jsonify([])

    tag = request.form.get('tag')
    id = request.form.get('id')
    last = request.form.get('last')

    engine = Engine.query.filter_by(id = id).first()
    tensor_path = os.path.join(engine.path, "model/tensorboard")
    files = glob.glob(os.path.join(tensor_path, "*"))

    last = int(last)
    
    if len(files) > 0:
        log = files[0]

        eacc = EventAccumulator(log)
        eacc.Reload()

        tags = eacc.Tags()

        stats = {}
        if tag in tags.get('scalars'):
            stats[tag] = []
            for data in eacc.Scalars(tag)[last:250]:
                stats[tag].append({ "time": data.wall_time, "step": data.step, "value": data.value })

        return jsonify({ "stopped": engine.status == "stopped", "stats": stats })
    else:
        return jsonify({ "stats": [], "stopped": False })

@train_blueprint.route('/train_status', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_status():
    if user_utils.is_normal(): return jsonify([])

    id = request.form.get('id')

    engine = Engine.query.filter_by(id = id).first()
    tensor_path = os.path.join(engine.path, "model/tensorboard")
    files = glob.glob(os.path.join(tensor_path, "*"))
    
    if len(files) > 0:
        log = files[0]

        eacc = EventAccumulator(log)
        eacc.Reload()

        stats = {}

        try:
            epoch_no = 0
            for data in eacc.Scalars("train/epoch"):
                if data.value > epoch_no:
                    epoch_no = data.value
            stats["epoch"] = epoch_no
        except:
            pass

        try:
            done = False
            for data in eacc.Scalars("train/done"):
                if data.value == 1:
                    done = True
            stats["done"] = done
        except:
            pass

        power = 0
        pynvml.nvmlInit()
        for i in range(0, pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            power = power + (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
        power = round(power / pynvml.nvmlDeviceGetCount())
            
        return jsonify({ "stopped": engine.status == "stopped", "stats": stats, "power": power })
    else:
        return jsonify({ "stats": [], "stopped": False })

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
    train_log_path = os.path.join(engine.path, 'model/train.log')

    rows = []
    try:
        with open(train_log_path, 'r') as train_log:
            i = 0
            for line in train_log:
                m = re.search(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}).*Epoch\s+(\d+)\sStep:\s+(\d+)\s+Batch Loss:\s+(\d+.\d+)\s+Tokens per Sec:\s+(\d+),\s+Lr:\s+(\d+.\d+)',
                                line.strip())

                if m:                
                    if i >= start and i < (start + length):
                            date_string = m.group(1)
                            time_string = m.group(2)
                            epoch, step = m.group(3), m.group(4)
                            batch_loss, tps, lr = m.group(5), m.group(6), m.group(7)

                            # date = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
                            rows.append([time_string, epoch, step, batch_loss, tps, lr])
                    i = i + 1
    except: 
        pass

    if start and length:
        rows = rows[start:length]

    if order is not None:
        rows.sort(key=lambda row: row[order], reverse=(dir == "desc"))

    rows_filtered = []
    if search:
        for row in rows:
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
        "data": rows_filtered if search else rows
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


@train_blueprint.route('/stop/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def train_stop(id):
    if user_utils.is_normal(): return redirect(url_for('index'))
    
    Trainer.stop(user_utils.get_uid(), id)

    return redirect(url_for('train.train_console', id=id))