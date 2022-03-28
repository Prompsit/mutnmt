from app import app, db
from app.models import File, Corpus, Corpus_File, LibraryCorpora, User, UserLanguage
from app.utils import utils, user_utils, data_utils, tasks
from app.flash import Flash
from flask import Blueprint, render_template, request, jsonify, flash, url_for, redirect
from flask_login import login_required, current_user
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

            source_lang = request.form.get('source_lang')
            target_lang = request.form.get('target_lang')

            custom_src_lang_code = request.form.get('sourceCustomLangCode')
            custom_trg_lang_code = request.form.get('targetCustomLangCode')

            if custom_src_lang_code:
                custom_src_lang_name = request.form.get('sourceCustomLangName')
                custom_lang = user_utils.add_custom_language(custom_src_lang_code, custom_src_lang_name)

                source_lang = custom_lang.id
            else:
                source_lang = UserLanguage.query.filter_by(code=source_lang, user_id=current_user.id).one().id

            if custom_trg_lang_code:
                custom_trg_lang_name = request.form.get('targetCustomLangName')
                custom_lang = user_utils.add_custom_language(custom_trg_lang_code, custom_trg_lang_name)

                target_lang = custom_lang.id
            else:
                target_lang = UserLanguage.query.filter_by(code=target_lang, user_id=current_user.id).one().id

            task_id = data_utils.process_upload_request(user_utils.get_uid(), request.files.get('bitext_file'), request.files.get('source_file'),
                    request.files.get('target_file'), source_lang, target_lang,
                    request.form.get('name'), request.form.get('description'), request.form.get('topic'))

            return jsonify({ "result": 200, "task_id": task_id })
        else:
            raise Exception("Sorry, but we couldn't handle your request.")
    except Exception as e:
        Flash.issue(e, Flash.ERROR)

    return jsonify({ "result": -1 })

@data_blueprint.route('/upload_status', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_status():
    task_id = request.form.get('task_id')
    task_success, task_value = utils.get_task_result(tasks.process_upload_request, task_id)
    if task_success is not None:
        if not task_success:
            exception_text = task_value if type(task_value) is Exception else None
            Flash.issue("Something went wrong" if exception_text is None else "Something went wrong: {}".format(exception_text), Flash.ERROR)
            return jsonify({ "result": -2 })

        Flash.issue("Corpus successfully uploaded and added to <a href='#your_corpora'>your corpora</a>.",
                    Flash.SUCCESS, markup=True)
        return jsonify({ "result": 200 })
    else:
        return jsonify({ "result": -1 })
