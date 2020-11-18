from app import app, db
from app.utils import user_utils, data_utils, utils, ttr
from app.utils.power import PowerUtils
from app.utils.GPUManager import GPUManager
from app.utils.translation.utils import TranslationUtils
from app.utils.translation.filetranslation import FileTranslation
from app.utils.translation.joeywrapper import JoeyWrapper
from app.utils.trainer import Trainer
from app.utils.tokenizer import Tokenizer
from app.models import Engine, Corpus, Corpus_Engine, Corpus_File, User, LibraryEngine, RunningEngines, LibraryCorpora
from app.flash import Flash
from celery import Celery
from werkzeug.datastructures import FileStorage
from nltk.tokenize import sent_tokenize
from werkzeug.utils import secure_filename
from lxml import etree


import pyter
import xlsxwriter
import datetime
import json
import os
import shutil
import yaml
import sys
import subprocess
import time
import pkgutil
import importlib
import inspect
import re
import redis

celery = Celery(app.name, broker = app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Engine training tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

@celery.task(bind=True)
def launch_training(self, user_id, engine_path, params):
    # Performs necessary steps to configure an engine
    # and get it ready for training

    engine = Engine(path = engine_path)
    engine.uploader_id = user_id
    engine.status = "launching"
    engine.bg_task_id = self.request.id

    db.session.add(engine)
    db.session.commit()

    used_corpora = {}

    try:
        os.mkdir(engine_path)
    except:
        Flash.issue("The engine could not be created", Flash.ERROR)
        return url_for('train.train_index', id=id)

    def join_corpora(list_name, phase, source_lang, target_lang):
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
                    corpus.corpus_files.append(Corpus_File(db_file, role="source" if file_entry.file.language_id == source_lang else "target"))
                    used_corpora[corpus_id] += corpus_size
            except:
                raise Exception

        db.session.add(corpus)
        db.session.commit()

        # We put the contents of the several files in a new single one, and we shuffle the sentences
        try:
            data_utils.join_corpus_files(corpus, shuffle=True, user_id=user_id)
        except:
            db.session.delete(corpus)
            db.session.commit()
            raise Exception

        return corpus

    try:
        train_corpus = join_corpora('training[]', phase="train", source_lang=params['source_lang'], target_lang=params['target_lang'])
        dev_corpus = join_corpora('dev[]', phase="dev", source_lang=params['source_lang'], target_lang=params['target_lang'])
        test_corpus = join_corpora('test[]', phase="test", source_lang=params['source_lang'], target_lang=params['target_lang'])

        # We train a SentencePiece model using the training corpus and we tokenize
        # everything with that. We save the model in the engine folder to tokenize
        # translation input later
        data_utils.train_tokenizer(engine, train_corpus, params['vocabularySize'])
        data_utils.tokenize(train_corpus, engine)
        data_utils.tokenize(dev_corpus, engine)
        data_utils.tokenize(test_corpus, engine)

        engine.name = params['nameText']
        engine.description = params['descriptionText']
        engine.source_id = params['source_lang']
        engine.target_id = params['target_lang']
        engine.model_path = os.path.join(engine.path, "model")

        engine.engine_corpora.append(Corpus_Engine(corpus=train_corpus, engine=engine, phase="train"))
        engine.engine_corpora.append(Corpus_Engine(corpus=dev_corpus, engine=engine, phase="dev"))
        engine.engine_corpora.append(Corpus_Engine(corpus=test_corpus, engine=engine, phase="test"))

        engine.status = "training_pending"
        engine.launched = datetime.datetime.utcnow().replace(tzinfo=None)

        user = User.query.filter_by(id = user_id).first()
        user.user_engines.append(LibraryEngine(engine=engine, user=user))

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
                tok_path = '{}.mut.spe'.format(file_entry.file.path)
                tok_name = phase

                os.link(tok_path, os.path.join(engine.path, '{}.{}'.format(tok_name, 
                        params['source_lang'] if file_entry.role == "source" else params['target_lang'])))

                config["data"][phase] = os.path.join(engine.path, tok_name)
                config["training"]["model_dir"] = os.path.join(engine.path, "model")

        try:
            link_files(train_corpus, "train")
            link_files(dev_corpus, "dev")
            link_files(test_corpus, "test")
        except:
            raise Exception 

        # Get vocabulary
        vocabulary_path = os.path.join(engine.path, "train.vocab")
        config["data"]["src_vocab"] = vocabulary_path
        config["data"]["trg_vocab"] = vocabulary_path
        
        config["name"] = engine.name
        config["training"]["epochs"] = int(params['epochsText'])
        config["training"]["patience"] = int(params['patienceTxt'])
        config["training"]["batch_size"] = int(params['batchSizeTxt'])
        config["training"]["validation_freq"] = int(params['validationFreq'])

        with open(config_file_path, 'w') as config_file:
            yaml.dump(config, config_file)

        engine.status = "ready"
        engine.bg_task_id = None
        db.session.commit()

        return engine.id
    except:
        db.session.delete(engine)
        db.session.commit()

        Flash.issue("The engine could not be configured", Flash.ERROR)
        return -1

@celery.task(bind=True)
def train_engine(self, engine_id, is_admin):
    # Trains an engine by calling JoeyNMT and keeping
    # track of its progress

    gpu_id = GPUManager.wait_for_available_device(is_admin=is_admin)

    try:

        engine = Engine.query.filter_by(id=engine_id).first()
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "{}".format(gpu_id)
        running_joey = subprocess.Popen(["python3", "-m", "joeynmt", "train", 
                                                os.path.join(engine.path, "config.yaml"), 
                                                "--save_attention"], cwd=app.config['JOEYNMT_FOLDER'],
                                                env=env)

        engine.status = "training"
        engine.pid = running_joey.pid
        db.session.commit()

        # Trainings are limited to 1 hour
        start = datetime.datetime.now()
        difference = 0

        while difference < 3600:
            time.sleep(10)
            difference = (datetime.datetime.now() - start).total_seconds()
            if running_joey.poll() is not None:
                # JoeyNMT finished (or died) before timeout
                db.session.refresh(engine)
                if engine.status != "stopped" and engine.status != "stopped_admin":
                    Trainer.stop(engine_id)
                GPUManager.free_device(gpu_id)
                return

        if running_joey.poll() is None:
            Trainer.stop(engine_id)
    finally:
        GPUManager.free_device(gpu_id)

@celery.task(bind=True)
def monitor_training(self, engine_id):    
    redis_conn = redis.Redis()
    
    def monitor():
        engine = Engine.query.filter_by(id=engine_id).first()
        if engine:
            if not engine.has_stopped():
                current_power = int(PowerUtils.get_mean_power())
                power = redis_conn.hget("power_value", engine_id)
                updates = redis_conn.hget("power_update", engine_id)

                power = int(power) if power else current_power
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

    monitor()

@celery.task(bind=True)
def test_training(self, engine_id):
    engine = Engine.query.filter_by(id=engine_id).first()
    test_dec_file = Corpus_File.query.filter_by(role = "target") \
                    .filter(Corpus_File.corpus_id.in_(db.session.query(Corpus_Engine.corpus_id) \
                    .filter_by(engine_id=engine_id, phase = "test", is_info=False))).first().file.path

    bleu = 0.0

    _, hyps_tmp_file = utils.tmpfile()
    _, test_crop_file = utils.tmpfile()
    joey_translate = subprocess.Popen("cat {} | head -n 2000 | python3 -m joeynmt translate -sm {} | tail -n +2 > {}" \
                                        .format(os.path.join(engine.path, 'test.' + engine.source.code), os.path.join(engine.path, 'config.yaml'), hyps_tmp_file),
                                        cwd=app.config['JOEYNMT_FOLDER'], shell=True)
    joey_translate.wait()

    decode_hyps = subprocess.Popen("cat {} | head -n 2000 | spm_decode --model={} --input_format=piece > {}.dec" \
                                        .format(hyps_tmp_file, os.path.join(engine.path, 'train.model'), hyps_tmp_file),
                                        cwd=app.config['MUTNMT_FOLDER'], shell=True)
    decode_hyps.wait()

    crop_test = subprocess.Popen("cat {} | head -n 2000 > {}".format(test_dec_file, test_crop_file), cwd=app.config['MUTNMT_FOLDER'], shell=True)
    crop_test.wait()

    sacreBLEU = subprocess.Popen("cat {}.dec | sacrebleu -b {}".format(hyps_tmp_file, test_crop_file), 
                        cwd=app.config['MUTNMT_FOLDER'], shell=True, stdout=subprocess.PIPE)
    sacreBLEU.wait()

    score = sacreBLEU.stdout.readline().decode("utf-8")

    engine.test_task_id = None
    engine.test_score = float(score)
    db.session.commit()

    return { "bleu": float(score) }

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# Translation tasks
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
def launch_engine(user_id, engine_id, is_admin):    
    user = User.query.filter_by(id=user_id).first()
    engine = Engine.query.filter_by(id=engine_id).first()
        
    translator = JoeyWrapper(engine.path, is_admin)
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
def translate_text(self, user_id, engine_id, lines, is_admin):    
    # We launch the engine
    translator, tokenizer = launch_engine(user_id, engine_id, is_admin)

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
def translate_file(self, user_id, engine_id, user_file_path, as_tmx, tmx_mode, is_admin):
    translator, tokenizer = launch_engine(user_id, engine_id, is_admin)
    file_translation = FileTranslation(translator, tokenizer)
    return file_translation.translate_file(user_id, user_file_path, as_tmx, tmx_mode)

@celery.task(bind=True)
def generate_tmx(self, user_id, engine_id, chain_engine_id, text, is_admin):
    translator, tokenizer = launch_engine(user_id, engine_id, is_admin)
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
def inspect_details(self, user_id, engine_id, line, engines, is_admin):
    translator, tokenizer = launch_engine(user_id, engine_id, is_admin)
    engine = Engine.query.filter_by(id=engine_id).first()

    inspect_details = None
    if line.strip() != "":
        sentences = sent_tokenize(line.strip())
        if len(sentences) > 0:
            line_tok = tokenizer.tokenize(sentences[0])
            n_best = translator.translate(line_tok, 5)
            del translator # Free GPU slot

            inspect_details = {
                "source": engine.source.code,
                "target": engine.target.code,
                "preproc_input": line_tok,
                "preproc_output": n_best[0],
                "nbest": [tokenizer.detokenize(n) for n in n_best],
                "alignments": [],
                "postproc_output": tokenizer.detokenize(n_best[0])
            }

    return inspect_details

@celery.task(bind=True)
def inspect_compare(self, user_id, line, engines, is_admin):
    translations = []
    for engine_id in engines:
        engine = Engine.query.filter_by(id = engine_id).first()
        translations.append(
            {
                "id": engine_id,
                "name": engine.name,
                "text": translate_text(user_id, engine_id, [line], is_admin)
            })

    return { "source": engine.source.code, "target": engine.target.code, "translations": translations }

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# EVALUATE TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@celery.task(bind=True)
def evaluate_files(self, user_id, mt_paths, ht_paths, source_path=None):

    # Load evaluators from ./evaluators folder
    evaluators: Evaluator = []
    for minfo in pkgutil.iter_modules([app.config['EVALUATORS_FOLDER']]):
        module = importlib.import_module('.{}'.format(minfo.name), package='app.blueprints.evaluate.evaluators')
        classes = inspect.getmembers(module)
        for name, _class in classes:
            if name != "Evaluator" and name.lower() == minfo.name.lower() and inspect.isclass(_class):
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
                    ht_eval.append({
                        "name": evaluator.get_name(),
                        "value": evaluator.get_value(mt_path, ht_path),
                        "is_metric": True
                    })
                except:
                    # If a metric throws an error because of things,
                    # we just skip it for now
                    pass

            ## Lexical variety for original, MT translation and reference
            for path in [mt_path, ht_path]:
                if path:
                    ht_eval.append({
                        "name": "{}".format("MT" if path == mt_path else "REF" if path == ht_path else ""),
                        "value": lexical_var.compute(path),
                        "is_metric": False
                    })

            evals.append(ht_eval)

        all_evals.append(evals)

    xlsx_file_paths = []
    ht_rows = []
    for ht_index, ht_path in enumerate(ht_paths):
        rows = []
        with open(ht_path, 'r') as ht_file:
            for i, line in enumerate(ht_file):
                line = line.strip()
                rows.append(["Ref {}".format(ht_index + 1), line, None, None, i + 1, []])

        for mt_path in mt_paths:
            scores = spl(mt_path, ht_path)
            for i, score in enumerate(scores):
                rows[i][5].append(score)

        if source_path:
            with open(source_path, 'r') as source_file:
                for i, line in enumerate(source_file):
                    rows[i].append(line.strip())
        
        xlsx_file_paths.append(generate_xlsx(user_id, rows, ht_index))

        ht_rows.append(rows)

    for path in (mt_paths + ht_paths):
        try:
            os.remove(path)
        except FileNotFoundError:
            # It was the same file, we just pass
            pass

    return { "result": 200, "evals": all_evals, "spl": ht_rows }, xlsx_file_paths

def spl(mt_path, ht_path):
    # Scores per line (bleu and ter)
    sacreBLEU = subprocess.Popen("cat {} | sacrebleu -sl -b {} > {}.bpl".format(mt_path, ht_path, mt_path), 
                        cwd=app.config['TMP_FOLDER'], shell=True, stdout=subprocess.PIPE)
    sacreBLEU.wait()

    rows = []
    with open('{}.bpl'.format(mt_path), 'r') as bl_file:
        rows = [ { "bleu": line.strip() } for line in bl_file]

    os.remove("{}.bpl".format(mt_path))

    with open(ht_path) as ht_file, open(mt_path) as mt_file:
        for i, row in enumerate(rows):
            ht_line = ht_file.readline().strip()
            mt_line = mt_file.readline().strip()
            if ht_line and mt_line:
                ter = round(pyter.ter(ht_line.split(), mt_line.split()), 2)
                rows[i]['ter'] = 100 if ter > 1 else utils.parse_number(ter * 100, 2)
                rows[i]['text'] = mt_line

    return rows

def generate_xlsx(user_id, rows, ht_path_index):
    file_name = utils.normname(user_id, "evaluation") + ".xlsx"
    file_path = utils.tmpfile(file_name)

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    x_rows = []
    for i, row in enumerate(rows):
        x_row = [i + 1, row[1]]

        if len(row) > 6:
            x_row = [i + 1, row[6], row[1]]
        
        for mt_data in row[5]:
            x_row.append(mt_data['text'])

        for mt_data in row[5]:
            x_row.append(mt_data['bleu'])

        for mt_data in row[5]:
            x_row.append(mt_data['ter'])

        x_rows.append(x_row)

    headers = ["Line"]
    if len(row) > 6:
        headers = headers + ["Source sentence", "Reference {}".format(ht_path_index + 1)]
    else:
        headers = headers + ["Reference {}".format(ht_path_index + 1)]


    headers = headers + ["Machine translation {}".format(i + 1) for i in range(len(row[5]))]
    headers = headers + ["Bleu MT{}".format(i + 1) for i in range(len(row[5]))]
    headers = headers + ["TER MT{}".format(i + 1) for i in range(len(row[5]))]

    x_rows = [headers] + x_rows

    row_cursor = 0
    for row in x_rows:
        for col_cursor, col in enumerate(row):
            worksheet.write(row_cursor, col_cursor, col)
        row_cursor  += 1

    workbook.close()

    return file_path

# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
# UPLOAD TASKS
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
@celery.task(bind=True)
def process_upload_request(self, user_id, bitext_path, src_path, trg_path, src_lang, trg_lang, corpus_name, corpus_desc="", corpus_topic=None):
    type = "bitext" if bitext_path else "bilingual" if trg_path else "monolingual"

    def process_file(file, language, corpus, role):
        db_file = data_utils.upload_file(file, language, user_id=user_id)

        if role == "source":
            corpus.source_id = language
        else:
            corpus.target_id = language
        
        db.session.add(db_file)
        corpus.corpus_files.append(Corpus_File(db_file, role=role))

        return db_file

    def process_bitext(file):
        file_name, file_extension = os.path.splitext(file.filename)
        norm_name = utils.normname(user_id=user_id, filename=file_name)
        tmp_file_fd, tmp_path = utils.tmpfile()
        file.save(tmp_path)

        if file_extension == ".tmx":
            with open(utils.filepath('FILES_FOLDER', norm_name + "-src"), 'wb') as src_file, \
            open(utils.filepath('FILES_FOLDER', norm_name + "-trg"), 'wb') as trg_file, \
            open(tmp_path, 'r') as tmx_file:
                tmx = etree.parse(tmx_file, etree.XMLParser())
                body = tmx.getroot().find("body")

                for tu in body.findall('.//tu'):
                    for i, tuv in enumerate(tu.findall('.//tuv')):
                        if i > 1: break
                        line = tuv.find("seg").text.strip()
                        line = re.sub(r'[\r\n\t\f\v]', " ", line)
                        dest_file = src_file if i == 0 else trg_file

                        dest_file.write(line.encode('utf-8'))
                        dest_file.write(os.linesep.encode('utf-8'))
        else:
            # We assume it is a TSV
            with open(utils.filepath('FILES_FOLDER', norm_name + "-src"), 'wb') as src_file, \
            open(utils.filepath('FILES_FOLDER', norm_name + "-trg"), 'wb') as trg_file, \
            open(tmp_path, 'r') as tmp_file:
                for line in tmp_file:
                    cols = line.strip().split('\t')
                    src_file.write((cols[0] + '\n').encode('utf-8'))
                    trg_file.write((cols[1] + '\n').encode('utf-8'))

        src_file = open(utils.filepath('FILES_FOLDER', norm_name + "-src"), 'rb')
        trg_file = open(utils.filepath('FILES_FOLDER', norm_name + "-trg"), 'rb')

        return FileStorage(src_file, filename=file.filename + "-src"), \
                FileStorage(trg_file, filename=file.filename + "-trg")

    # We create the corpus, retrieve the files and attach them to that corpus
    target_db_file = None
    try:
        corpus = Corpus(name = corpus_name, type = "bilingual" if type == "bitext" else type, 
                    owner_id = user_id, description = corpus_desc, topic_id = corpus_topic)

        if type == "bitext":
            with open(bitext_path, 'rb') as fbitext:
                bitext_file = FileStorage(fbitext, filename=os.path.basename(fbitext.name))
                src_file, trg_file = process_bitext(bitext_file)

                source_db_file = process_file(src_file, src_lang, corpus, 'source')
                target_db_file = process_file(trg_file, trg_lang, corpus, 'target')
        else:
            with open(src_path, 'rb') as fsrctext:
                src_file = FileStorage(fsrctext, filename=os.path.basename(fsrctext.name))
                source_db_file = process_file(src_file, src_lang, corpus, 'source')

            if type == "bilingual":
                with open(trg_path, 'rb') as ftrgtext:
                    trg_file = FileStorage(ftrgtext, filename=os.path.basename(ftrgtext.name))
                    target_db_file = process_file(trg_file, trg_lang, corpus, 'target')

        db.session.add(corpus)

        user = User.query.filter_by(id=user_id).first()
        user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
    except Exception as e:
        db.session.rollback()
        raise Exception("Something went wrong on our end... Please, try again later")

    if target_db_file:
        source_lines = utils.file_length(source_db_file.path)
        target_lines = utils.file_length(target_db_file.path)

        if source_lines != target_lines:
            db.session.rollback()
            raise Exception("Source and target file should have the same length")

    db.session.commit()

    return True