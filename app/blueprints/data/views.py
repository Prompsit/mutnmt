from app import app, db
from app.models import File, Corpus, Corpus_File, LibraryCorpora, User, Language
from app.utils import utils, user_utils, data_utils
from app.flash import Flash
from flask import Blueprint, render_template, request, jsonify, flash, url_for, redirect
from flask_login import login_required
from sqlalchemy import desc

import os
import subprocess
import hashlib
import re
import datetime
import shutil
import sys

data_blueprint = Blueprint('data', __name__, template_folder='templates')

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

    return render_template('preview.data.html.jinja2', page_name='library_corpora_file_preview', file=file, lines=lines)

@data_blueprint.route('/upload', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_perform():
    type = "bilingual" if "target_file" in request.files.keys() else "monolingual"

    if user_utils.is_normal(): return redirect(url_for('index'))

    try:
        if request.method == 'POST':
            def process_file(file, language, corpus, role):
                db_file = data_utils.upload_file(file, language)

                if role == "source":
                    corpus.source_id = language
                else:
                    corpus.target_id = language
                
                db.session.add(db_file)
                corpus.corpus_files.append(Corpus_File(db_file, role=role))

                return db_file

            # We create the corpus, retrieve the files and attach them to that corpus
            target_db_file = None
            try:
                corpus = Corpus(name = request.form['name'], type = type, 
                            owner_id = user_utils.get_uid(), description = request.form['description'])

                source_db_file = process_file(request.files.get('source_file'), request.form['source_lang'], corpus, 'source')

                if type == "bilingual":
                    target_db_file = process_file(request.files.get('target_file'), request.form['target_lang'], corpus, 'target')

                db.session.add(corpus)

                user = User.query.filter_by(id=user_utils.get_uid()).first()
                user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
            except Exception as e:
                raise e
                print(e, file=sys.stderr)
                raise Exception("Something went wrong on our end... Please, try again later")

            if target_db_file:
                source_lines = utils.file_length(source_db_file.path)
                target_lines = utils.file_length(target_db_file.path)
                
                if source_lines != target_lines:
                    raise Exception("Source and target file should have the same length")

            db.session.commit()
        else:
            raise Exception("Sorry, but we couldn't handle your request")
    except Exception as e:
        Flash.issue(e, Flash.ERROR)
    else:
        Flash.issue("Corpus successfully uploaded and added to <a href='#your_corpora'>your corpora</a>.", Flash.SUCCESS, markup=True)

    return request.referrer
