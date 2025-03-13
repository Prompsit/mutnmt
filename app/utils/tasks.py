import datetime
import importlib
import inspect
import json
import logging
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.parsers.expat

import pyter
import redis
import xlsxwriter
import yaml
from celery import Celery
from celery.signals import task_postrun, task_prerun
from flask import url_for
from flask_login import current_user
from nltk.tokenize import sent_tokenize
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import app, db
from app.flash import Flash
from app.models import (
    Corpus,
    Corpus_Engine,
    Corpus_File,
    Engine,
    LibraryCorpora,
    LibraryEngine,
    RunningEngines,
    User,
    UserLanguage,
)
from app.utils import data_utils, ttr, user_utils, utils
from app.utils.GPUManager import GPUManager
from app.utils.power import PowerUtils
from app.utils.roles import EnumRoles
from app.utils.tokenizer import Tokenizer
from app.utils.trainer import Trainer
from app.utils.translation.filetranslation import FileTranslation
from app.utils.translation.marianwrapper import MarianWrapper
from app.utils.translation.utils import TranslationUtils

celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Engine training tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


@celery.task(bind=True)
def launch_training(self, user_id, engine_path, params):
    def join_corpora(list_name, phase, source_lang, target_lang, engine_id):
        with app.app_context():
            corpus = Corpus(owner_id=user_id, visible=False)
            for train_corpus in params[list_name]:
                corpus_data = json.loads(train_corpus)
                corpus_id = corpus_data["id"]
                corpus_size = corpus_data["size"]

                if corpus_id not in used_corpora:
                    used_corpora[corpus_id] = 0

                try:
                    og_corpus = Corpus.query.filter_by(id=corpus_id).first()

                    # We relate the original corpus with this engine in the database,
                    # for informational purposes. This way the user will be able to know
                    # which corpora were used to train the engine
                    engine = db.session.query(Engine).filter_by(id=engine_id).first()
                    engine.engine_corpora.append(
                        Corpus_Engine(
                            corpus=og_corpus,
                            engine=engine,
                            phase=phase,
                            is_info=True,
                            selected_size=corpus_size,
                        )
                    )

                    corpus.user_source_id = og_corpus.user_source_id
                    corpus.user_target_id = og_corpus.user_target_id
                    for file_entry in og_corpus.corpus_files:
                        with open(file_entry.file.path, "rb") as file_d:
                            db_file = data_utils.upload_file(
                                FileStorage(
                                    stream=file_d, filename=file_entry.file.name
                                ),
                                file_entry.file.user_language_id,
                                selected_size=corpus_size,
                                offset=used_corpora[corpus_id],
                                user_id=user_id,
                            )
                        corpus.corpus_files.append(
                            Corpus_File(
                                db_file,
                                role=(
                                    "source"
                                    if file_entry.file.language.code == source_lang
                                    else "target"
                                ),
                            )
                        )
                    used_corpora[corpus_id] += corpus_size
                except Exception as ex:
                    print(ex, flush=True)
                    raise ex

            try:
                db.session.add(corpus)
                db.session.commit()
            except:
                db.session.rollback()
                raise Exception

                # We put the contents of the several files in a new single one, and we shuffle the sentences
                try:
                    data_utils.join_corpus_files(corpus, shuffle=True, user_id=user_id)
                except:
                    db.session.delete(corpus)
                    db.session.commit()
                    raise Exception

            return corpus.id

    try:
        with app.app_context():
            # Performs necessary steps to configure an engine
            # and get it ready for training

            engine = Engine(path=engine_path)
            engine.uploader_id = user_id
            engine.status = "launching"
            engine.bg_task_id = self.request.id

            db.session.add(engine)
            db.session.commit()

            used_corpora = {}

            try:
                os.makedirs(engine_path)
            except:
                Flash.issue("The engine could not be created", Flash.ERROR)
                return url_for("train.train_index", id=id)

            train_corpus_id = join_corpora(
                "training[]",
                phase="train",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
            )
            dev_corpus_id = join_corpora(
                "dev[]",
                phase="dev",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
            )
            test_corpus_id = join_corpora(
                "test[]",
                phase="test",
                source_lang=params["source_lang"],
                target_lang=params["target_lang"],
                engine_id=engine.id,
            )

            train_corpus = (
                db.session.query(Corpus).filter_by(id=train_corpus_id).first()
            )
            dev_corpus = db.session.query(Corpus).filter_by(id=dev_corpus_id).first()
            test_corpus = db.session.query(Corpus).filter_by(id=test_corpus_id).first()

            #######
            # this whole section is unneeded for Marian - commented for now - delete later
            # We train a SentencePiece model using the training corpus and we tokenize
            # everything with that. We save the model in the engine folder to tokenize
            # translation input later
            # data_utils.train_tokenizer(engine, train_corpus_id, params['vocabularySize'])
            # data_utils.tokenize(train_corpus_id, engine)
            # data_utils.tokenize(dev_corpus_id, engine)
            # data_utils.tokenize(test_corpus_id, engine)
            #######

            engine.name = params["nameText"]
            engine.description = params["descriptionText"]

            # set engine model path and create the folder so Marian can use it
            engine.model_path = os.path.join(engine.path, "model")
            os.mkdir(engine.model_path)

            print("########################################", flush=True)
            print("########################################", flush=True)
            print("########################################", flush=True)

            print("-- ENGINE PATH: " + engine.path, flush=True)
            print("-- ENGINE MODEL PATH: " + engine.model_path, flush=True)

            print("########################################", flush=True)
            print("########################################", flush=True)
            print("########################################", flush=True)

            source_lang = UserLanguage.query.filter_by(
                code=params["source_lang"], user_id=user_id
            ).one()
            engine.user_source_id = source_lang.id

            target_lang = UserLanguage.query.filter_by(
                code=params["target_lang"], user_id=user_id
            ).one()
            engine.user_target_id = target_lang.id

            engine.engine_corpora.append(
                Corpus_Engine(corpus=train_corpus, engine=engine, phase="train")
            )
            engine.engine_corpora.append(
                Corpus_Engine(corpus=dev_corpus, engine=engine, phase="dev")
            )
            engine.engine_corpora.append(
                Corpus_Engine(corpus=test_corpus, engine=engine, phase="test")
            )

            engine.status = "training_pending"
            engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)

            # user = db.session.query(User).filter_by(id=user_id).first()
            user = User.query.filter_by(id=user_id).first()
            user.user_engines.append(LibraryEngine(engine=engine, user=user))

            config_file_path = os.path.join(engine.path, "config.yaml")

            # get Marian engine configuration
            shutil.copyfile(
                os.path.join(
                    app.config["BASE_CONFIG_FOLDER"], "transformer-marian.yaml"
                ),
                config_file_path,
            )

            db.session.add(engine)
            db.session.commit()

            config = None

            try:
                with open(config_file_path, "r") as config_file:
                    config = yaml.load(config_file, Loader=yaml.FullLoader)
            except:
                raise Exception

            def link_files(corpus, phase):
                try:
                    sets_arr = []
                    for file_entry in corpus.corpus_files:
                        # create split filename and create path to it
                        split_name = "{}.{}".format(
                            phase,
                            (
                                params["source_lang"]
                                if file_entry.role == "source"
                                else params["target_lang"]
                            ),
                        )
                        split_path = str(os.path.join(engine.path, split_name))

                        # link corpus path to split path
                        corpus_path = file_entry.file.path
                        os.link(corpus_path, split_path)

                        sets_arr.append(split_path)

                    # insert it to configs in Marian style for train and valid sets, e.g. "train-sets" array
                    if phase != "test":
                        set_name = f"{phase}-sets"
                        config[set_name] = sets_arr

                except Exception as ex:
                    logging.exception("An exception was thrown in LINK_FILES")

            # link set files and insert in config file
            link_files(train_corpus, "train")
            link_files(dev_corpus, "valid")
            link_files(test_corpus, "test")

            # call marian-vocab to create vocabulary files
            data_utils.marian_vocab(
                engine,
                params["source_lang"],
                params["target_lang"],
                params["vocabularySize"],
            )

            # set vocabulary paths and dimensions, setting paths to .spm
            # so marian can automatically train a sentencepiece tokenizer
            src_vocab = os.path.join(
                engine.path, f"vocab.{params['source_lang']}{params['target_lang']}.spm"
            )
            trg_vocab = os.path.join(
                engine.path, f"vocab.{params['source_lang']}{params['target_lang']}.spm"
            )
            config["vocabs"] = [src_vocab, trg_vocab]
            config["dim-vocabs"] = [params["vocabularySize"], params["vocabularySize"]]

            # set paths to model files and to training log
            config["model"] = os.path.join(engine.path, "model/model.npz")
            config["log"] = os.path.join(engine.path, "model/train.log")

            # set user values for epochs, early stopping patience and validation frequency
            config["after"] = f"{params['epochsText']}e"
            config["early-stopping"] = int(params["patienceTxt"])
            config["valid-freq"] = int(params["validationFreq"])

            config["mini-batch"] = int(params['batchSizeTxt'])
            config["beam-size"] = int(params['beamSizeTxt'])

            with open(config_file_path, "w") as config_file:
                yaml.dump(config, config_file)

            engine.status = "ready"
            engine.bg_task_id = None
            db.session.commit()

            return engine.id
    except Exception as ex:
        with app.app_context():
            db.session.delete(engine)
            db.session.commit()

            # Flash.issue("The engine could not be configured", Flash.ERROR)
            logging.exception("An exception was thrown!")
            return -1

def add_graph_log(engine_model_path, engine_path):
    try:
        # log the newly created graph_dict.yaml into the graph_logs.yaml file
        dict_path = os.path.join(engine_model_path, "graph_dict.yaml")
        graph_log = os.path.join(engine_path, "graph_logs.yaml")

        if os.path.exists(graph_log):
            with open(graph_log, "r") as f:
                graphs_dict = yaml.load(f, Loader = yaml.FullLoader)

            new_index = max(graphs_dict.keys()) + 1
            graphs_dict[new_index] = dict_path

            with open(graph_log, "w") as f:
                yaml.dump(graphs_dict, f)
        else:
            graphs_dict = {}
            graphs_dict[1] = dict_path

            with open(graph_log, "w") as f:
                yaml.dump(graphs_dict, f)
    except:
        logging.exception("An exception was thrown in ADD_GRAPH_LOG!")

def refresh_full_graph_log(engine_path):
    try:
        # this function will be called throughout the training process to create
        # and update a log yaml file with all the relevant training values for graph drawing

        full_graph_log = os.path.join(engine_path, "full_graph.yaml")
        graph_log = os.path.join(engine_path, "graph_logs.yaml")

        # if graph logs yaml file does not exist, then just exit to not crash the functions
        if not os.path.exists(graph_log):
            return

        with open(graph_log, "r") as f:
            graph_paths = yaml.load(f, Loader = yaml.FullLoader)

        full_dict = {}
        first_log = True
        for graph_path in graph_paths.values():
            with open(graph_path, "r") as f:
                graph_dict = yaml.load(f, Loader = yaml.FullLoader)
            
            if first_log:
                full_dict = graph_dict
                first_log = False
            else:
                for key in graph_dict.keys():
                    if key != "train/train_epoch":
                        # get the final step in the current key
                        max_step = max([i["step"] for i in full_dict[key]])

                        for i, item in enumerate(graph_dict[key]):
                            # increment the current step by the amount of the final step in the key
                            # to have a realistic and gradual increase in training steps
                            graph_dict[key][i]["step"] = item["step"] + max_step

                        full_dict[key] += graph_dict[key]
                    else:
                        # if key is epochs, then just copy whatever is there
                        full_dict["train/train_epoch"] += graph_dict["train/train_epoch"]
                    
        with open(full_graph_log, "w") as f:
            yaml.dump(full_dict, f)
    except:
        logging.exception("An exception was thrown in REFRESH_FULL_GRAPH_LOG!")

@celery.task(bind=True)
def train_engine(self, engine_id, user_role, retrain_path=""):
    # Trains an engine by calling JoeyNMT and keeping
    # track of its progress
    try:
        with app.app_context():
            engine = Engine.query.filter_by(id=engine_id).first()
            engine.status = "launching"
            db.session.commit()
            gpu_id = GPUManager.wait_for_available_device(
                is_admin=(user_role == EnumRoles.ADMIN)
            )
            engine.gid = gpu_id
            db.session.commit()

            try:
                env = os.environ.copy()

                # set Marian pretrained path if the user wants to start training the model again
                marian_pretrained_cmd = ""
                if retrain_path != "" and os.path.exists(retrain_path):
                    marian_pretrained_cmd = f"--pretrained-model {retrain_path}"

                print(
                    "---- PRETRAINED MODEL: {0}".format(marian_pretrained_cmd),
                    flush=True,
                )

                # get Marian training command and set available GPUs in environment
                config_path = os.path.join(engine.path, "config.yaml")
                marian_cmd = "{0}/build/marian -c {1} {2}".format(
                    app.config["MARIAN_FOLDER"], config_path, marian_pretrained_cmd
                )
                env["CUDA_VISIBLE_DEVICES"] = "{}".format(gpu_id)

                print('--------------------------------', flush = True)
                print(marian_cmd, flush = True)
                print('--------------------------------', flush = True)

                print("---- CUDA DEVICES: {0}".format(gpu_id))
                print("CONFIG PATH: " + str(config_path))
                print("DOES CONFIG EXIST: " + str(os.path.isfile(config_path)))

                print("------- BEFORE STARTING MARIAN", flush=True)
                # run Marian training command
                # popen command must be run with shell functionality, and a process group must be created
                # with preexec_fn in order to be able to kill the process later with SIGTERM, else it won't stop
                marian_process = subprocess.Popen(marian_cmd, env=env, shell=True, preexec_fn = os.setsid)
                print("-- PID: " + str(marian_process.pid), flush = True)
                print("------- AFTER STARTING MARIAN", flush = True)

                engine.status = "training"
                engine.pid = marian_process.pid
                db.session.commit()
                
                # add the graph log path to the logs file for historic use
                add_graph_log(engine.model_path, engine.path)

                print("-- ENGINE PID: " + str(engine.pid), flush = True)
                print("-- ENGINE ID: " + str(engine_id) + " / " + str(engine.id), flush = True)
                print("-- ENGINE PATH: " + str(engine.path), flush = True)
                print("-- ENGINE MODEL PATH: " + str(engine.model_path), flush = True)

                # trainings are limited to 1 hour unless user has researcher or admin role
                start = datetime.datetime.now()
                difference = 0
                max_time = (
                    36000
                    if (
                        user_role == EnumRoles.RESEARCHER
                        or user_role == EnumRoles.ADMIN
                    )
                    else 3600
                )
                while difference < max_time:
                    time.sleep(10)
                    difference = (datetime.datetime.now() - start).total_seconds()
                    if marian_process.poll() is not None:
                        # training process finished (or died) before timeout
                        db.session.refresh(engine)
                        if (engine.status != "stopped" and engine.status != "stopped_admin"):
                            Trainer.stop(engine_id)
                        GPUManager.free_device(gpu_id)
                        refresh_full_graph_log(engine.path)
                        return

                if marian_process.poll() is None:
                    refresh_full_graph_log(engine.path)
                    Trainer.stop(engine_id)

            except Exception as ex:
                logging.exception("An exception was thrown in TRAIN_ENGINE!")
            finally:
                engine.status = "stopped"
                GPUManager.free_device(gpu_id)
                db.session.commit()
                refresh_full_graph_log(engine.path)
    except Exception as ex:
        logging.exception("An exception was thrown in TRAIN_ENGINE!")


@celery.task(bind=True)
def monitor_training(self, engine_id):
    redis_conn = redis.Redis()

    def monitor():
        try:
            with app.app_context():
                engine = Engine.query.filter_by(id=engine_id).first()
                if engine:
                    if not engine.has_stopped():
                        current_power = int(PowerUtils.get_mean_power(engine.gid))
                        power = redis_conn.hget("power_value", engine_id)
                        updates = redis_conn.hget("power_update", engine_id)

                        power = int(power) if power else 0
                        updates = int(updates) + 1 if updates else 1

                        redis_conn.hset("power_value", engine_id, power + current_power)
                        redis_conn.hset("power_update", engine_id, updates)
                        engine.power = int(power + current_power) / updates
                        db.session.commit()

                        time.sleep(10)
                        monitor()
                else:
                    time.sleep(5)
                    monitor()
        except Exception as ex:
            logging.exception("An exception was thrown in MONITOR!")

    monitor()


@celery.task(bind=True)
def test_training(self, engine_id):
    with app.app_context():
        try:
            engine = Engine.query.filter_by(id=engine_id).first()
            test_dec_file = (
                Corpus_File.query.filter_by(role="target")
                .filter(
                    Corpus_File.corpus_id.in_(
                        db.session.query(Corpus_Engine.corpus_id).filter_by(
                            engine_id=engine_id, phase="test", is_info=False
                        )
                    )
                )
                .first()
                .file.path
            )

            bleu = 0.0

            _, hyps_tmp_file = utils.tmpfile()
            _, test_crop_file = utils.tmpfile()
            joey_translate = subprocess.Popen(
                "cat {} | head -n 2000 | python3 -m joeynmt translate {} > {}".format(
                    os.path.join(engine.path, "test." + engine.source.code),
                    os.path.join(engine.path, "config.yaml"),
                    hyps_tmp_file,
                ),
                cwd=app.config["JOEYNMT_FOLDER"],
                shell=True,
            )
            joey_translate.wait()

            decode_hyps = subprocess.Popen(
                "cat {} | head -n 2000 | spm_decode --model={} --input_format=piece > {}.dec".format(
                    hyps_tmp_file,
                    os.path.join(engine.path, "train.model"),
                    hyps_tmp_file,
                ),
                cwd=app.config["MUTNMT_FOLDER"],
                shell=True,
            )
            decode_hyps.wait()

            crop_test = subprocess.Popen(
                "cat {} | head -n 2000 > {}".format(test_dec_file, test_crop_file),
                cwd=app.config["MUTNMT_FOLDER"],
                shell=True,
            )
            crop_test.wait()

            sacreBLEU = subprocess.Popen(
                "cat {}.dec | sacrebleu -b {}".format(hyps_tmp_file, test_crop_file),
                cwd=app.config["MUTNMT_FOLDER"],
                shell=True,
                stdout=subprocess.PIPE,
            )
            sacreBLEU.wait()

            score = sacreBLEU.stdout.readline().decode("utf-8")

            engine.test_task_id = None
            engine.test_score = float(score)
            db.session.commit()

            return {"bleu": float(score)}
        except Exception as e:
            db.session.rollback()
            raise e


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Translation tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


def launch_engine(user_id, engine_id):
    with app.app_context():
        user = User.query.filter_by(id=user_id).first()
        engine = Engine.query.filter_by(id=engine_id).first()
        # If this user is already using another engine, we switch
        user_engine = RunningEngines.query.filter_by(user_id=user_id).delete()
        if user_engine:
            db.session.delete(user_engine)

        user.user_running_engines.append(RunningEngines(engine=engine, user=user))
        db.session.commit()
        translator = MarianWrapper(engine.model_path)

    return translator  # , tokenizer


@celery.task(bind=True)
def translate_text(self, user_id, engine_id, lines):
    translator = launch_engine(user_id, engine_id)
    translations = translator.translate(lines)

    with app.app_context():
        try:
            db.session.delete(RunningEngines.query.filter_by(user_id=user_id).first())
            db.session.commit()
        except:
            db.session.rollback()
    return translations


@celery.task(bind=True)
def translate_file(self, user_id, engine_id, user_file_path, as_tmx, tmx_mode):
    translator = launch_engine(user_id, engine_id)
    file_translation = FileTranslation(translator)
    return file_translation.translate_file(user_id, user_file_path, as_tmx, tmx_mode)


@celery.task(bind=True)
def generate_tmx(self, user_id, engine_id, chain_engine_id, text):
    translator = launch_engine(user_id, engine_id)
    file_translation = FileTranslation(translator)

    if chain_engine_id:
        translations = []
        for line in text:
            if line.strip() != "":
                for sentence in sent_tokenize(line):
                    translation = translator.translate(sentence)
                    translations.append(translation)
            else:
                translations.append("")

        text = translations

    return file_translation.text_as_tmx(user_id, text)


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# INSPECT TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


@celery.task(bind=True)
def inspect_details(self, user_id, engine_id, line):
    translator = launch_engine(user_id, engine_id)
    with app.app_context():
        engine = Engine.query.filter_by(id=engine_id).first()
        tokenizer = Tokenizer(engine)
        tokenizer.load()
        inspect_details = None
        if line.strip() != "":
            line_tok = tokenizer.tokenize(line)
            n_best = translator.translate([line], n_best=True)
            sentences = []
            for sent in n_best:
                sentences.append(sent.split("|||")[1])
            del translator  # Free GPU slot

            inspect_details = {
                "source": engine.source.code,
                "target": engine.target.code,
                "preproc_input": line_tok,
                "preproc_output": tokenizer.tokenize(sentences[0]),
                "nbest": sentences,
                "alignments": [],
                "postproc_output": sentences[0],
            }

    return inspect_details


@celery.task(bind=True)
def inspect_compare(self, user_id, line, engines):
    translations = []
    with app.app_context():
        for engine_id in engines:
            engine = Engine.query.filter_by(id=engine_id).first()
            translations.append(
                {
                    "id": engine_id,
                    "name": engine.name,
                    "text": translate_text(user_id, engine_id, [line]),
                }
            )

        return {
            "source": engine.source.code,
            "target": engine.target.code,
            "translations": translations,
        }


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# EVALUATE TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@celery.task(bind=True)
def evaluate_files(self, user_id, mt_paths, ht_paths, source_path=None):
    # Transform utf-8 with BOM (if it is) to utf-8
    for path in mt_paths + ht_paths + [source_path]:
        if path:
            data_utils.convert_file_to_utf8(path)
            data_utils.fix_file(path)

    # Load evaluators from ./evaluators folder
    evaluators: Evaluator = []
    for minfo in pkgutil.iter_modules([app.config["EVALUATORS_FOLDER"]]):
        module = importlib.import_module(
            ".{}".format(minfo.name), package="app.blueprints.evaluate.evaluators"
        )
        classes = inspect.getmembers(module)
        for name, _class in classes:
            if (
                name != "Evaluator"
                and name.lower() == minfo.name.lower()
                and inspect.isclass(_class)
            ):
                evaluator = getattr(module, name)
                evaluators.append(evaluator())

    lexical_var = ttr.Ttr()
    all_evals = []
    for mt_path in mt_paths:
        evals = []

        for ht_path in ht_paths:
            ht_eval = []
            for evaluator in evaluators:
                try:
                    ht_eval.append(
                        {
                            "name": evaluator.get_name(),
                            "value": evaluator.get_value(mt_path, ht_path, source_path),
                            "is_metric": True,
                        }
                    )
                except:
                    # If a metric throws an error because of things,
                    # we just skip it for now
                    pass

            ## Lexical variety for original, MT translation and reference
            for path in [mt_path, ht_path]:
                if path:
                    ht_eval.append(
                        {
                            "name": "{}".format(
                                "MT"
                                if path == mt_path
                                else "REF" if path == ht_path else ""
                            ),
                            "value": lexical_var.compute(path),
                            "is_metric": False,
                        }
                    )

            evals.append(ht_eval)

        all_evals.append(evals)

    xlsx_file_paths = []
    ht_rows = []
    for ht_index, ht_path in enumerate(ht_paths):
        rows = []
        with open(ht_path, "r") as ht_file:
            for i, line in enumerate(ht_file):
                line = line.strip()
                rows.append(
                    ["Ref {}".format(ht_index + 1), line, None, None, i + 1, []]
                )

        for mt_path in mt_paths:
            scores = spl(mt_path, ht_path, source_path)
            for i, score in enumerate(scores):
                rows[i][5].append(score)

        if source_path:
            with open(source_path, "r") as source_file:
                for i, line in enumerate(source_file):
                    rows[i].append(line.strip())

        xlsx_file_paths.append(generate_xlsx(user_id, rows, ht_index))

        ht_rows.append(rows)

    for path in mt_paths + ht_paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            # It was the same file, we just pass
            pass

    return {"result": 200, "evals": all_evals, "spl": ht_rows}, xlsx_file_paths


def spl(mt_path, ht_path, source_path):
    # Scores per line (bleu, comet, chrf3 and ter)
    logger.info([mt_path, ht_path])
    rows = []

    # Obtain Bleu results in output file
    sacreBLEU = subprocess.Popen(
        "cat {} | sacrebleu -sl -b {} > {}.bpl".format(mt_path, ht_path, mt_path),
        cwd=app.config["TMP_FOLDER"],
        shell=True,
        stdout=subprocess.PIPE,
    )
    sacreBLEU.wait()

    # Obtain CHRF3 results in output file
    sacreCHRF = subprocess.Popen(
        "cat {} | sacrebleu -sl -b {} -m chrf --chrf-beta 3 > {}.chrfpl".format(
            mt_path, ht_path, mt_path
        ),
        cwd=app.config["TMP_FOLDER"],
        shell=True,
        stdout=subprocess.PIPE,
    )
    sacreCHRF.wait()

    # Obtain Comet results in output file
    if source_path != "":
        src_path = "-s {0}".format(source_path)

    comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} -o {3}.cpl".format(mt_path, src_path, ht_path, mt_path),
                            shell=True, stdout=subprocess.PIPE)

    # UNCOMMENT FOR CPU COMET !!!
    # comet = subprocess.run("pymarian-eval -m wmt22-comet-da -l comet -t {0} {1} -r {2} -o {3}.cpl -c 8".format(mt_path, src_path, ht_path, mt_path),
    #                shell=True, stdout=subprocess.PIPE)
    ##############################

    # Bleu rows
    with open("{}.bpl".format(mt_path), "r") as bl_file:
        rows = [{"bleu": line.strip()} for line in bl_file]
    os.remove("{}.bpl".format(mt_path))

    # Comet and CHRF3 rows
    with open("{}.cpl".format(mt_path), "r") as cl_file, open(
        "{}.chrfpl".format(mt_path), "r"
    ) as chrfl_file:
        for i, row in enumerate(rows):
            score_cl = cl_file.readline().strip()
            score_chrfl = chrfl_file.readline().strip()
            rows[i]["comet"] = score_cl
            rows[i]["chrf3"] = score_chrfl
    os.remove("{}.cpl".format(mt_path))
    os.remove("{}.chrfpl".format(mt_path))

    # TER rows
    with open(ht_path) as ht_file, open(mt_path) as mt_file:
        for i, row in enumerate(rows):
            ht_line = ht_file.readline().strip()
            mt_line = mt_file.readline().strip()
            if ht_line and mt_line:
                ter = round(pyter.ter(ht_line.split(), mt_line.split()), 2)
                rows[i]["ter"] = 100 if ter > 1 else utils.parse_number(ter * 100, 2)
                rows[i]["text"] = mt_line

    return rows


def generate_xlsx(user_id, rows, ht_path_index):
    file_name = utils.normname(user_id, "evaluation") + ".xlsx"
    file_path = utils.tmpfile(file_name)

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    x_rows = []
    for i, row in enumerate(rows):
        x_row = [i + 1]

        if len(row) > 6:
            x_row = [i + 1, row[6]]

        for mt_data in row[5]:
            x_row.append(mt_data["text"])

        x_row.append(row[1])

        for mt_data in row[5]:
            x_row.append(mt_data["bleu"])

        for mt_data in row[5]:
            x_row.append(mt_data["ter"])

        x_rows.append(x_row)

    headers = ["Line"]
    headers = headers + (["Source sentence"] if len(row) > 6 else [])
    headers = headers + [
        "Machine translation {}".format(i + 1) for i in range(len(row[5]))
    ]
    headers = headers + ["Reference {}".format(ht_path_index + 1)]

    headers = headers + ["Bleu MT{}".format(i + 1) for i in range(len(row[5]))]
    headers = headers + ["TER MT{}".format(i + 1) for i in range(len(row[5]))]

    x_rows = [headers] + x_rows

    row_cursor = 0
    for row in x_rows:
        for col_cursor, col in enumerate(row):
            worksheet.write(row_cursor, col_cursor, col)
        row_cursor += 1

    workbook.close()

    return file_path


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# UPLOAD TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@celery.task(bind=True)
def process_upload_request(
    self,
    user_id,
    bitext_path,
    src_path,
    trg_path,
    src_lang,
    trg_lang,
    corpus_name,
    corpus_desc="",
    corpus_topic=None,
):
    type = "bitext" if bitext_path else "bilingual" if trg_path else "monolingual"

    def process_file(file, language, corpus, role):
        with app.app_context():
            db_file = data_utils.upload_file(file, language, user_id=user_id)

            if role == "source":
                corpus.user_source_id = language
            else:
                corpus.user_target_id = language

            db.session.add(db_file)
            corpus.corpus_files.append(Corpus_File(db_file, role=role))

        return db_file

    def process_bitext(file):
        file_name, file_extension = os.path.splitext(file.filename)
        norm_name = utils.normname(user_id=user_id, filename=file_name)
        tmp_file_fd, tmp_path = utils.tmpfile()
        file.save(tmp_path)

        data_utils.convert_file_to_utf8(tmp_path)
        data_utils.fix_file(tmp_path)

        if file_extension == ".tmx":
            with open(
                utils.filepath("FILES_FOLDER", norm_name + "-src"), "w"
            ) as src_file, open(
                utils.filepath("FILES_FOLDER", norm_name + "-trg"), "w"
            ) as trg_file, open(
                tmp_path, "rb"
            ) as tmx_file:
                inside_tuv = False
                seg_text = []
                tu = []

                def se(name, _):
                    nonlocal inside_tuv
                    if name == "seg":
                        inside_tuv = True

                def lp(line):
                    return re.sub(r"[\r\n\t\f\v]", " ", line.strip())

                def ee(name):
                    nonlocal inside_tuv, seg_text, tu, src_file
                    if name == "seg":
                        inside_tuv = False
                        tu.append("".join(seg_text))
                        seg_text = []

                        if len(tu) == 2:
                            print(lp(tu[0]), file=src_file)
                            print(lp(tu[1]), file=trg_file)
                            tu = []

                def cd(data):
                    nonlocal inside_tuv, seg_text
                    if inside_tuv:
                        seg_text.append(data)

                parser = xml.parsers.expat.ParserCreate()
                parser.StartElementHandler = se
                parser.EndElementHandler = ee
                parser.CharacterDataHandler = cd
                parser.ParseFile(tmx_file)

        else:
            # We assume it is a TSV
            with open(
                utils.filepath("FILES_FOLDER", norm_name + "-src"), "wb"
            ) as src_file, open(
                utils.filepath("FILES_FOLDER", norm_name + "-trg"), "wb"
            ) as trg_file, open(
                tmp_path, "r"
            ) as tmp_file:
                for line in tmp_file:
                    cols = line.strip().split("\t")
                    src_file.write((cols[0] + "\n").encode("utf-8"))
                    trg_file.write((cols[1] + "\n").encode("utf-8"))

        src_file = open(utils.filepath("FILES_FOLDER", norm_name + "-src"), "rb")
        trg_file = open(utils.filepath("FILES_FOLDER", norm_name + "-trg"), "rb")

        return FileStorage(src_file, filename=file.filename + "-src"), FileStorage(
            trg_file, filename=file.filename + "-trg"
        )

    with app.app_context():
        # We create the corpus, retrieve the files and attach them to that corpus
        target_db_file = None
        try:
            corpus = Corpus(
                name=corpus_name,
                type="bilingual" if type == "bitext" else type,
                owner_id=user_id,
                description=corpus_desc,
                topic_id=corpus_topic,
            )

            if type == "bitext":
                with open(bitext_path, "rb") as fbitext:
                    bitext_file = FileStorage(
                        fbitext, filename=os.path.basename(fbitext.name)
                    )
                    src_file, trg_file = process_bitext(bitext_file)

                    source_db_file = process_file(src_file, src_lang, corpus, "source")
                    target_db_file = process_file(trg_file, trg_lang, corpus, "target")
            else:
                with open(src_path, "rb") as fsrctext:
                    src_file = FileStorage(
                        fsrctext, filename=os.path.basename(fsrctext.name)
                    )
                    source_db_file = process_file(src_file, src_lang, corpus, "source")

                if type == "bilingual":
                    with open(trg_path, "rb") as ftrgtext:
                        trg_file = FileStorage(
                            ftrgtext, filename=os.path.basename(ftrgtext.name)
                        )
                        target_db_file = process_file(
                            trg_file, trg_lang, corpus, "target"
                        )

            db.session.add(corpus)

            user = User.query.filter_by(id=user_id).first()
            user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
        except Exception as e:
            db.session.rollback()
            raise Exception(
                "Something went wrong on our end... Please, try again later"
            )

        if target_db_file:
            source_lines = utils.file_length(source_db_file.path)
            target_lines = utils.file_length(target_db_file.path)

            if source_lines != target_lines:
                db.session.rollback()
                raise Exception("Source and target file should have the same length")

        db.session.commit()

    return True


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Pre- post- tasks to allocate GPUs for translation
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


@task_prerun.connect
def reserve_gpu(sender=None, **kwargs):
    name = sender.name.split(".")[-1]
    is_admin = sender.request.args[-1]
    if name in (
        "translate_text",
        "translate_file",
        "inspect_details",
        "inspect_compare",
    ):
        device = GPUManager.wait_for_available_device(is_admin=is_admin)
        if device is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = str(device)
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
        logging.debug(f"Task {sender.name}[{sender.request.id}] reserved GPU {device}")


@task_postrun.connect
def free_gpu(sender=None, **kwargs):
    name = sender.name.split(".")[-1]
    if name in (
        "translate_text",
        "translate_file",
        "inspect_details",
        "inspect_compare",
    ):
        if os.environ["CUDA_VISIBLE_DEVICES"]:
            device = os.environ["CUDA_VISIBLE_DEVICES"]
            GPUManager.free_device(int(device))
            logging.debug(f"Task {sender.name}[{sender.request.id}] freed GPU {device}")
