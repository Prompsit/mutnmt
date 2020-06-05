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
    if user_utils.is_normal(): return redirect(url_for('index'))

    try:
        if request.method == 'POST':
            data_utils.process_upload_request(user_utils.get_uid(), request.files.get('bitext_file'), request.files.get('source_file'),
                    request.files.get('target_file'), request.form.get('source_lang'), request.form.get('target_lang'),
                    request.form.get('name'), request.form.get('description'))
        else:
            raise Exception("Sorry, but we couldn't handle your request")
    except Exception as e:
        raise e
        Flash.issue(e, Flash.ERROR)
    else:
        Flash.issue("Corpus successfully uploaded and added to <a href='#your_corpora'>your corpora</a>.", Flash.SUCCESS, markup=True)

    return request.referrer
