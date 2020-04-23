from app import app, db
from app.models import File, Corpus, Corpus_File, LibraryCorpora, User, Language
from app.utils import utils, user_utils
from app.flash import Flash
from flask import Blueprint, render_template, request, jsonify, flash, url_for, redirect
from flask_login import login_required
from random import randint
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import desc

import os
import subprocess
import hashlib
import re
import datetime
import shutil
import sys

import sentencepiece as spm

data_blueprint = Blueprint('data', __name__, template_folder='templates')

@data_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_index():
    if user_utils.is_normal(): return redirect(url_for('index'))

    corpora = Corpus.query.filter_by(owner_id = user_utils.get_uid()).all()

    return render_template('data.html.jinja2', page_name='data', corpora = corpora)

@data_blueprint.route('/upload/<type>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload(type):
    if user_utils.is_normal(): return redirect(url_for('index'))

    languages = Language.query.all()
    return render_template('upload.data.html.jinja2', page_name='data', type=type, languages=languages)

@data_blueprint.route('/preview/<file_id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_preview(file_id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    file = File.query.filter_by(id=file_id).first()
    lines = []
    with open(file.path, 'r') as reader:
        for i, line in enumerate(reader):
            if i < 50:
                lines.append(line)
            else:
                break

    return render_template('preview.data.html.jinja2', page_name='data', file=file, lines=lines)

@data_blueprint.route('/upload/<type>/perform', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_perform(type):
    if user_utils.is_normal(): return redirect(url_for('index'))

    try:
        if request.method == 'POST':
            try:
                # Data folder
                source_file = request.files.get('source_file')
                source_db_file = upload_file(source_file, request.form['source_lang'])

                corpus = Corpus(name = request.form['name'], type = type, owner_id = user_utils.get_uid())
                corpus.corpus_files.append(Corpus_File(source_db_file, role="source"))
                corpus.source_id = request.form['source_lang']
                
                if type == "bilingual":
                    target_file = request.files.get('target_file')
                    target_db_file = upload_file(target_file, request.form['target_lang'])
                    corpus.files.append(target_db_file)
                    corpus.target_id = request.form['target_lang']
            except Exception as e:
                print(e, file=sys.stderr)
                raise Exception("Database error")

            try:
                tokenize(corpus)
            except Exception as e:
                print(e, file=sys.stderr)
                raise Exception("Tokenization error")
            else:
                db.session.add(corpus)
                db.session.commit()
        else:
            raise Exception("Request not allowed")
    except Exception as e:
        Flash.issue(e, Flash.ERROR)
    else:
        Flash.issue("Corpus successfully uploaded!", Flash.SUCCESS)

    return url_for('data.data_index')

def upload_file(file, language):
    norm_name = utils.normname(user_id=user_utils.get_uid(), filename=file.filename)
    path = os.path.join(app.config['FILES_FOLDER'], norm_name)
    
    # Could we already have it stored?
    blake = hashlib.blake2b()
    while True:
        data = file.read(65536)
        if not data: break
        blake.update(data)

    hash = blake.hexdigest()

    query = File.query.filter_by(hash = hash)
    db_file = None

    try:
        db_file = query.first()
        if db_file is None: raise NoResultFound

        os.link(db_file.path, path)
        os.link('{}.mut.spe'.format(db_file.path), '{}.mut.spe'.format(path))

        db_file = File(path = path, name = file.filename, uploaded = db_file.uploaded,
                        hash = hash, uploader_id = user_utils.get_uid(), language_id = db_file.language_id,
                        lines = db_file.lines, words = db_file.words, chars = db_file.chars)
        
    except NoResultFound:
        file.seek(0)
        file.save(path)

        # Get file stats
        wc_output = subprocess.check_output('wc -lwc {}'.format(path), shell=True)
        wc_output_search = re.search(r'^(\s*)(\d+)(\s+)(\d+)(\s+)(\d+)(.*)$', wc_output.decode("utf-8"))
        lines, words, chars = wc_output_search.group(2),  wc_output_search.group(4),  wc_output_search.group(6)

        # Save in DB
        db_file = File(path = path, name = file.filename, language_id = language,
                        hash = hash, uploader_id = user_utils.get_uid(),
                        lines = lines, words = words, chars = chars,
                        uploaded = datetime.datetime.utcnow())
    finally:
        if db_file is not None:
            db.session.add(db_file)
            db.session.commit()

    return db_file

def tokenize(corpus):
    model_path = os.path.join(app.config['FILES_FOLDER'], 'mut.{}.model'.format(corpus.id))
    vocab_path = os.path.join(app.config['FILES_FOLDER'], 'mut.{}.vocab'.format(corpus.id))

    try:
        os.stat(model_path)
    except:
        files_list = []
        for file_entry in corpus.corpus_files:
            files_list.append(file_entry.file.path)
        files = " ".join(files_list)
        random_sample_path = "{}.mut.10k".format(corpus.id)
        cat_proc = subprocess.Popen("cat {} | shuf | head -n 10000 > {}".format(files, random_sample_path), shell=True)
        cat_proc.wait()

        spm.SentencePieceTrainer.Train("--input={} --model_prefix=mut.{} --vocab_size=6000 --hard_vocab_limit=false".format(random_sample_path, corpus.id))
        shutil.move(os.path.join(app.config['MUTNMT_FOLDER'], "mut.{}.model".format(corpus.id)), model_path)
        shutil.move(os.path.join(app.config['MUTNMT_FOLDER'], "mut.{}.vocab".format(corpus.id)), vocab_path)
        os.remove(random_sample_path)
        
        purge_vocab = subprocess.Popen("cat {} | awk -F '\\t' '{{ print $1 }}' > {}.purged".format(vocab_path, vocab_path), shell=True)
        purge_vocab.wait()

        os.remove(vocab_path)
        shutil.move("{}.purged".format(vocab_path), vocab_path)

    for entry_file in corpus.corpus_files:
        file_tok_path = '{}.mut.spe'.format(entry_file.file.path)

        try:
            os.stat(file_tok_path)
        except:
            sp = spm.SentencePieceProcessor()
            sp.Load(model_path)
            with open(file_tok_path, 'w+') as file_tok:
                with open(entry_file.file.path) as file:
                    for line in file:
                        line_encoded = sp.EncodeAsPieces(line)
                        print("".join(line_encoded), file=file_tok)