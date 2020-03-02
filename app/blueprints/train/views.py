from app import app, db
from app.models import LibraryCorpora, Engine, File, Corpus_Engine, Corpus
from app.utils import user_utils
from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import func
from toolwrapper import ToolWrapper
import datetime

import hashlib
import os
import yaml
import shutil
import sys
import logging

train_blueprint = Blueprint('train', __name__, template_folder='templates')

running_joey = {}

@train_blueprint.route('/')
def train_index():
    currently_training = Engine.query.filter_by(uploader_id = user_utils.get_uid()) \
                            .filter(Engine.status != "done").all()

    if (len(currently_training) > 0):
        return redirect(url_for('train.train_console', id=currently_training[0].id))

    corpora = Corpus.query.filter_by(owner_id = user_utils.get_uid()).all()
    return render_template('train.html.jinja2', page_name='train', corpora=corpora)

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

    try:
        os.mkdir(engine_path)
    except:
        return ""
    
    shutil.copyfile(os.path.join(app.config['BASE_CONFIG_FOLDER'], 'transformer.yaml'), os.path.join(engine_path, 'config.yaml'))

    db.session.add(engine)
    db.session.commit()

    return redirect(url_for('train.train_launch', id=engine.id))

@train_blueprint.route('/launch/<id>')
def train_launch(id):
    engine = Engine.query.filter_by(id=id).first()
    
    if user_utils.get_uid() in running_joey.keys():
        running_joey[user_utils.get_uid()].close()
        del running_joey[user_utils.get_uid()]

    config_file_path = os.path.join(engine.path, 'config.yaml')
    config = None
    print(config_file_path, file=sys.stderr)
    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
    except:
        pass

    try:
        os.mkdir(os.path.join(engine.path, "model"))
    except:
        pass


    def link_files(corpus, phase):
        for file_entry in corpus.corpus_files:
            try:
                os.link(file_entry.file.path, os.path.join(engine.path, file_entry.file.name))
            except:
                pass

            config["data"][phase] = os.path.join(engine.path, file_entry.file.name)
            config["training"]["model_dir"] = os.path.join(engine.path, "model")

    corpus_train = Corpus_Engine.query.filter_by(engine_id = engine.id, phase="train").first().corpus
    link_files(corpus_train, "train")

    corpus_dev = Corpus_Engine.query.filter_by(engine_id = engine.id, phase="dev").first().corpus
    link_files(corpus_dev, "dev")

    corpus_test = Corpus_Engine.query.filter_by(engine_id = engine.id, phase="test").first().corpus
    link_files(corpus_test, "test")
    
    config["name"] = engine.name

    with open(config_file_path, 'w') as config_file:
        yaml.dump(config, config_file)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)

    slave = ToolWrapper(["python3", "-m", "joeynmt", "train", os.path.join(engine.path, "config.yaml"), "-sm"],
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

@train_blueprint.route('/stop/<id>')
def train_stop(id):
    if user_utils.get_uid() in running_joey.keys():
        running_joey[user_utils.get_uid()].close()
        del running_joey[user_utils.get_uid()]

    engine = Engine.query.filter_by(id = id).first()
    shutil.rmtree(engine.path)
    db.session.delete(engine)
    db.session.commit()

    return redirect(url_for('train.train_index'))