from app import app, db
from app.models import File, Corpus, Corpus_File, LibraryCorpora, User
from app.utils import utils, user_utils
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
import sys

import sentencepiece as spm

data_blueprint = Blueprint('data', __name__, template_folder='templates')

@data_blueprint.route('/')
def data_index():
    corpora = Corpus.query.filter_by(owner_id = user_utils.get_uid()).all()

    print(corpora, file=sys.stderr)

    return render_template('data.html.jinja2', page_name='data', corpora = corpora)

@data_blueprint.route('/upload/<type>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload(type):
    return render_template('upload.data.html.jinja2', page_name='data', type=type)

@data_blueprint.route('/upload/<type>/perform', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_perform(type):
    if request.method == 'POST':
        # Data folder
        blake = hashlib.blake2b()
        blake.update('{}{}'.format(user_utils.get_user().username, request.form['name']).encode("utf-8"))
        name_footprint = blake.hexdigest()[:16]

        source_file = request.files.get('source_file')
        source_db_file = upload_file(source_file, name_footprint, request.form['source_lang'])

        corpus = Corpus(name = request.form['name'], type = type, owner_id = user_utils.get_uid())
        corpus.corpus_files.append(Corpus_File(source_db_file, role="source"))
        corpus.source_id = request.form['source_lang']
        
        if type == "bilingual":
            target_file = request.files.get('target_file')
            target_db_file = upload_file(target_file, name_footprint, request.form['target_lang'])
            corpus.files.append(target_db_file)
            corpus.target_id = request.form['target_lang']

        db.session.add(corpus)
        db.session.commit()

        flash('Corpus uploaded successfully')
    else:
        flash('Error while uploading corpus')

    return redirect(url_for('data.data_index'))

def upload_file(file, footprint, language):
    norm_name = '{}-{}-{}'.format(footprint, file.filename, randint(1, 100000))
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
            user = User.query.filter_by(id = user_utils.get_uid()).first()
            user.user_files.append(LibraryCorpora(file=db_file, user=user))
            db.session.add(db_file)
            db.session.commit()

    return db_file

def tokenize(corpus):
    basename = os.path.splittext(file.path)[0]
    model_name = '{}.model'.format(basename)

    try:
        os.stat(model_name)
    except:
        
        model_feed = subprocess.Popen("cat {} {} | shuf | head -n 10000".format(), shell=True)