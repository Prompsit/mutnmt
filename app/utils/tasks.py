from app import app, db
from app.utils import user_utils, data_utils
from app.utils.power import PowerUtils
from app.utils.translation.utils import TranslationUtils
from app.utils.translation.filetranslation import FileTranslation
from app.utils.translation.joeywrapper import JoeyWrapper
from app.utils.trainer import Trainer
from app.utils.tokenizer import Tokenizer
from app.models import Engine, Corpus, Corpus_Engine, Corpus_File, User, LibraryEngine, RunningEngines
from app.flash import Flash
from celery import Celery
from werkzeug.datastructures import FileStorage
from nltk.tokenize import sent_tokenize

import datetime
import json
import os
import shutil
import yaml
import sys
import subprocess
import time

celery = Celery(app.name, broker = app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Engine training tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

@celery.task(bind=True)
def launch_training(self, user_id, engine_path, params):
    # Performs necessary steps to configure an engine
    # and get it ready for training

    engine = Engine(path = engine_path)
    used_corpora = {}

    def join_corpora(list_name, phase):
        corpus = Corpus(owner_id=user_id, visible=False)
        for train_corpus in params[list_name]:
            corpus_data = json.loads(train_corpus)
            corpus_id = corpus_data['id']
            corpus_size = corpus_data['size']

            if corpus_id not in used_corpora: used_corpora[corpus_id] = 0

            try:
                og_corpus = Corpus.query.filter_by(id = corpus_id).first()

                # We relate the original corpus with this engine in the database,
                # for informational purposes. This way the user will be able to know
                # which corpora were used to train the engine
                engine.engine_corpora.append(Corpus_Engine(corpus=og_corpus, engine=engine, phase=phase, is_info=True, selected_size=corpus_size))

                corpus.source_id = og_corpus.source_id
                corpus.target_id = og_corpus.target_id
                for file_entry in og_corpus.corpus_files:
                    with open(file_entry.file.path, 'rb') as file_d:
                        db_file = data_utils.upload_file(FileStorage(stream=file_d, filename=file_entry.file.name), 
                                    file_entry.file.language_id, selected_size=corpus_size, offset=used_corpora[corpus_id],
                                    user_id=user_id)
                    corpus.corpus_files.append(Corpus_File(db_file, role=file_entry.role))
                    used_corpora[corpus_id] += corpus_size
            except:
                raise Exception

        db.session.add(corpus)
        db.session.commit()

        # We put the contents of the several files in a new single one, and we shuffle the sentences
        try:
            data_utils.join_corpus_files(corpus, shuffle=True, user_id=user_id)
            data_utils.tokenize(corpus)
        except:
            db.session.delete(corpus)
            db.session.commit()
            raise Exception

        return corpus

    try:
        train_corpus = join_corpora('training[]', phase="train")
        dev_corpus = join_corpora('dev[]', phase="dev")
        test_corpus = join_corpora('test[]', phase="test")

        engine.name = params['nameText']
        engine.description = params['descriptionText']
        engine.source = train_corpus.source
        engine.target = train_corpus.target

        engine.engine_corpora.append(Corpus_Engine(corpus=train_corpus, engine=engine, phase="train"))
        engine.engine_corpora.append(Corpus_Engine(corpus=dev_corpus, engine=engine, phase="dev"))
        engine.engine_corpora.append(Corpus_Engine(corpus=test_corpus, engine=engine, phase="test"))

        engine.status = "training_pending"
        engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)
        engine.uploader_id = user_id

        user = User.query.filter_by(id = user_id).first()
        user.user_engines.append(LibraryEngine(engine=engine, user=user))

        try:
            os.mkdir(engine_path)
        except:
            Flash.issue("The engine could not be created", Flash.ERROR)
            return url_for('train.train_index', id=id)

        config_file_path = os.path.join(engine.path, 'config.yaml')

        shutil.copyfile(os.path.join(app.config['BASE_CONFIG_FOLDER'], 'transformer.yaml'), config_file_path)

        db.session.add(engine)
        db.session.commit()

        # Engine configuration
        config = None

        try:
            with open(config_file_path, 'r') as config_file:
                config = yaml.load(config_file, Loader=yaml.FullLoader)
        except:
            raise Exception

        config["data"]["src"] = engine.source.code
        config["data"]["trg"] = engine.target.code

        def link_files(corpus, phase):
            for file_entry in corpus.corpus_files:
                print([file_entry.file.id, file_entry.file.path], file=sys.stderr)
                tok_path = '{}.mut.spe'.format(file_entry.file.path)
                tok_name = phase

                os.link(tok_path, os.path.join(engine.path, '{}.{}'.format(tok_name, 
                        config["data"]["src" if file_entry.role == "source" else "trg"])))

                config["data"][phase] = os.path.join(engine.path, tok_name)
                config["training"]["model_dir"] = os.path.join(engine.path, "model")

        try:
            link_files(train_corpus, "train")
            link_files(dev_corpus, "dev")
            link_files(test_corpus, "test")
        except:
            raise Exception 

        # Get vocabulary
        vocabulary_path = os.path.join(app.config['FILES_FOLDER'], 'mut.{}.vocab'.format(train_corpus.id))
        final_vocabulary_path = os.path.join(engine.path, "train.vocab")

        extract_vocabulary = subprocess.Popen("cat {} | head -n {} > {}".format(vocabulary_path, params['vocabularySize'], final_vocabulary_path),
                                shell=True)

        extract_vocabulary.wait()

        config["data"]["src_vocab"] = final_vocabulary_path
        config["data"]["trg_vocab"] = final_vocabulary_path

        config["name"] = engine.name
        config["training"]["epochs"] = int(params['epochsText'])
        config["training"]["patience"] = int(params['patienceTxt'])
        config["training"]["batch_size"] = int(params['batchSizeTxt'])

        with open(config_file_path, 'w') as config_file:
            yaml.dump(config, config_file)

        engine.status = "ready"
        db.session.commit()

        return engine.id
    except:
        db.session.delete(engine)
        db.session.commit()

        Flash.issue("The engine could not be configured", Flash.ERROR)
        return -1

@celery.task(bind=True)
def train_engine(self, engine_id):
    # Trains an engine by calling JoeyNMT and keeping
    # track of its progress

    engine = Engine.query.filter_by(id=engine_id).first()
    running_joey = subprocess.Popen(["python3", "-m", "joeynmt", "train", 
                                            os.path.join(engine.path, "config.yaml"), 
                                            "--save_attention"], cwd=app.config['JOEYNMT_FOLDER'])

    engine.status = "training"
    engine.pid = running_joey.pid
    db.session.commit()

    # Trainings are limited to 1 hour
    time.sleep(3600)

    if running_joey.poll() is None:
        Trainer.stop(engine_id)

@celery.task(bind=True)
def monitor_training(self, engine_id):
    def monitor():
        engine = Engine.query.filter_by(id=engine_id).first()
        if engine:
            while not engine.has_stopped():
                power = PowerUtils.get_mean_power()
                engine.power = int(power)
                db.session.commit()
                time.sleep(10)
        else:
            time.sleep(5)
            monitor()

    monitor()

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Translation tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
def launch_engine(user_id, engine_id):
    user = User.query.filter_by(id=user_id).first()
    engine = Engine.query.filter_by(id=engine_id).first()
    
    translator = JoeyWrapper(engine.path)
    translator.load()

    # If this user is already using another engine, we switch
    user_engine = RunningEngines.query.filter_by(user_id=user_id).first()
    if user_engine: db.session.delete(user_engine)

    user.user_running_engines.append(RunningEngines(engine=engine, user=user))
    db.session.commit()

    tokenizer = Tokenizer(engine)
    tokenizer.load()

    return translator, tokenizer

@celery.task(bind=True)
def translate_text(self, user_id, engine_id, lines):    
    # We launch the engine
    translator, tokenizer = launch_engine(user_id, engine_id)

    # We translate
    translations = []
    for line in lines:
        if line.strip() != "":
            for sentence in sent_tokenize(line):
                line_tok = tokenizer.tokenize(sentence)
                translation = translator.translate(line_tok)
                translations.append(tokenizer.detokenize(translation))
        else:
            translations.append("")

    return translations

@celery.task(bind=True)
def translate_file(self, user_id, engine_id, user_file_path, as_tmx, tmx_mode):
    translator, tokenizer = launch_engine(user_id, engine_id)
    file_translation = FileTranslation(translator, tokenizer)
    return file_translation.translate_file(user_id, user_file_path, as_tmx, tmx_mode)

@celery.task(bind=True)
def generate_tmx(self, user_id, engine_id, chain_engine_id, text):
    translator, tokenizer = launch_engine(user_id, engine_id)
    file_translation = FileTranslation(translator, tokenizer)

    if chain_engine_id:
        translations = []
        for line in text:
            if line.strip() != "":
                for sentence in sent_tokenize(line):
                    line_tok = tokenizer.tokenize(sentence)
                    translation = translator.translate(line_tok)
                    translations.append(tokenizer.detokenize(translation))
            else:
                translations.append("")

        text = translations

    return file_translation.text_as_tmx(user_id, text)

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# INSPECT TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

@celery.task(bind=True)
def inspect_details(self, user_id, engine_id, line):
    translator, tokenizer = launch_engine(user_id, engine_id)
    engine = Engine.query.filter_by(id=engine_id).first()

    n_best = []
    if line.strip() != "":
        line_tok = tokenizer.tokenize(line)
        n_best = translator.translate(line_tok, 5)
    else:
        return None

    return {
        "source": engine.source.code,
        "target": engine.target.code,
        "preproc_input": line_tok,
        "preproc_output": n_best[0],
        "nbest": [tokenizer.detokenize(n) for n in n_best],
        "alignments": [],
        "postproc_output": tokenizer.detokenize(n_best[0])
    }
@celery.task(bind=True)
def inspect_compare(self, user_id, engines, text):
    translations = []
    for engine_id in engines:
        engine = Engine.query.filter_by(id = engine_id).first()
        translations.append(
            {
                "id": engine_id,
                "name": engine.name,
                "text": translate_text(user_id, engine_id, [text])
            })

    return { "source": engine.source.code, "target": engine.target.code, "translations": translations }