from app import app, db
from app.models import LibraryCorpora, LibraryEngine, Engine, File, Corpus_Engine, Corpus, User
from app.utils import user_utils
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_file
from sqlalchemy import func
from toolwrapper import ToolWrapper
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import namegenerator
import datetime

import hashlib
import os
import yaml
import shutil
import sys
import logging
import ntpath
import subprocess
import glob

train_blueprint = Blueprint('train', __name__, template_folder='templates')

running_joey = {}

@train_blueprint.route('/')
def train_index():
    currently_training = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status.like("training")).all()
    
    random_name = namegenerator.gen()
    tryout = 0
    while len(Engine.query.filter_by(name = random_name).all()):
        random_name = namegenerator.gen()
        tryout += 1

        if tryout >= 5:
            random_name = ""
            break

    random_name = " ".join(random_name.split("-")[:2])

    if (len(currently_training) > 0):
        return redirect(url_for('train.train_console', id=currently_training[0].id))

    corpora = Corpus.query.filter_by(owner_id = user_utils.get_uid()).all()
    return render_template('train.html.jinja2', page_name='train', corpora=corpora, random_name=random_name)

@train_blueprint.route('/start', methods=['POST'])
def train_start():
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
    if user_utils.get_uid() in running_joey.keys():
        running_joey[user_utils.get_uid()].close()
        del running_joey[user_utils.get_uid()]

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
def train_launch(id):
    engine = Engine.query.filter_by(id=id).first()
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)

    slave = ToolWrapper(["python3", "-m", "joeynmt", "train", os.path.join(engine.path, "config.yaml"), "--save_attention"],
                        cwd=app.config['JOEYNMT_FOLDER'])

    running_joey[user_utils.get_uid()] = slave

    return redirect(url_for('train.train_console', id=id))

@train_blueprint.route('/console/<id>')
def train_console(id):
    engine = Engine.query.filter_by(id = id).first()
    config_file_path = os.path.join(engine.path, 'config.yaml')
    config = None

    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
    except:
        pass

    return render_template("train_console.html.jinja2", page_name="train",
            engine=engine, config=config,
            launched = datetime.datetime.timestamp(engine.launched))

@train_blueprint.route('/graph_data', methods=["POST"])
def train_graph():
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

        return jsonify(stats)
    else:
        return jsonify([])

@train_blueprint.route('/attention/<id>')
def train_attention(id):
    engine = Engine.query.filter_by(id = id).first()
    files = glob.glob(os.path.join(engine.path, "*.att"))
    if len(files) > 0:
        return send_file(files[0])
    else:
        return send_file(os.path.join(app.config['BASE_CONFIG_FOLDER'], "attention.png"))


@train_blueprint.route('/stop/<id>')
def train_stop(id):
    if user_utils.get_uid() in running_joey.keys():
        running_joey[user_utils.get_uid()].close()
        del running_joey[user_utils.get_uid()]

    engine = Engine.query.filter_by(id = id).first()
    engine.status = "stopped"
    db.session.commit()

    return redirect(url_for('train.train_index'))