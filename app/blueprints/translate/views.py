from app import app
from app.flash import Flash
from app.models import LibraryEngine, Engine
from app.utils import user_utils, utils, tasks
from app.utils.translation.utils import TranslationUtils
from flask import Blueprint, render_template, request, send_file, after_this_request, url_for, redirect, jsonify
from werkzeug.utils import secure_filename
from celery.result import AsyncResult

import subprocess, sys, logging, os, glob, shutil

translate_blueprint = Blueprint('translate', __name__, template_folder='templates')
        
translators = TranslationUtils()

@translate_blueprint.route('/')
def translate_index():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()).all()
    return render_template('translate.html.jinja2', page_name='translate_text', page_title='Translate', engines = engines)

@translate_blueprint.route('/leave', methods=['POST'])
def translate_leave():
    translators.deattach(user_utils.get_uid())
    return "true"

@translate_blueprint.route('/text', methods=["POST"])
def translate_text():
    engine_id = request.form.get('engine_id')
    lines = request.form.getlist('text[]')
    detached = True
    translation_task_id = translators.text(user_utils.get_uid(), engine_id, lines)

    return jsonify({ "result": 200, "task_id": translation_task_id })

@translate_blueprint.route('/file', methods=['POST'])
def upload_file():
    engine_id = request.form.get('engine_id')
    user_file = request.files.get('user_file')
    as_tmx = request.form.get('as_tmx') == 'true'
    tmx_mode = request.form.get('tmx_mode')
    
    key = utils.normname(user_utils.get_uid(), user_file.filename)
    this_upload = user_utils.get_user_folder(key)

    try:
        os.mkdir(this_upload)
    except:
        shutil.rmtree(this_upload)
        os.mkdir(this_upload)
    
    user_file_path = os.path.join(this_upload, secure_filename(user_file.filename))
    user_file.save(user_file_path)

    translation_task_id = translators.translate_file(user_utils.get_uid(), engine_id, user_file_path, as_tmx, tmx_mode)

    return jsonify({ "result": 200, "task_id": translation_task_id })

@translate_blueprint.route('/get', methods=["POST"])
def get_translation():
    task_id = request.form.get('task_id')
    result = tasks.translate_text.AsyncResult(task_id)
    if result and result.status == "SUCCESS":
        return { "result": 200, "lines": result.get() }
    else:
        return { "result": -1 }

@translate_blueprint.route('/get_file', methods=["POST"])
def get_file_translation():
    task_id = request.form.get('task_id')
    result = tasks.translate_text.AsyncResult(task_id)
    if result and result.status == "SUCCESS":
        return { "result": 200, "url": url_for('translate.download_file', key=task_id) }
    else:
        return { "result": -1 }

@translate_blueprint.route('/download/<key>')
def download_file(key):
    result = tasks.translate_text.AsyncResult(key)
    file_path = result.get()
    if result and result.status == "SUCCESS":
        return send_file(file_path, as_attachment=True)
    else:
        return "-1"

@translate_blueprint.route('/as_tmx', methods=["POST"])
def as_tmx():
    engine_id = request.form.get('engine_id')
    chain_engine_id = request.form.get('chain_engine_id')
    chain_engine_id = chain_engine_id if chain_engine_id and chain_engine_id != "false" else None
    text = request.form.getlist('text[]')

    translation_task_id = translators.generate_tmx(user_utils.get_uid(), engine_id, chain_engine_id, text)
    return jsonify({ "result": 200, "task_id": translation_task_id })

@translate_blueprint.route('/get_tmx', methods=["POST"])
def get_tmx():
    task_id = request.form.get('task_id')
    result = tasks.generate_tmx.AsyncResult(task_id)
    if result and result.status == "SUCCESS":
        return { "result": 200, "url": url_for('translate.download_file', key=task_id) }
    else:
        return { "result": -1 }
