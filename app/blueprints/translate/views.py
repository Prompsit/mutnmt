from app import app
from app.models import LibraryEngine, Engine
from app.utils import user_utils, translation_utils, utils
from flask import Blueprint, render_template, request, send_file, after_this_request
from werkzeug.utils import secure_filename

import subprocess, sys, logging, os, glob, shutil

translate_blueprint = Blueprint('translate', __name__, template_folder='templates')
        
translators = translation_utils.TranslationUtils()

@translate_blueprint.route('/')
@translate_blueprint.route('/text')
def translate_index():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()).all()
    return render_template('text_translate.html.jinja2', page_name='translate_text', engines = engines)

@translate_blueprint.route('/files')
def translate_files():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()).all()
    return render_template('files_translate.html.jinja2', page_name='translate_files', engines = engines)

@translate_blueprint.route('/attach_engine/<id>')
def translate_attach(id):
    if translators.launch(user_utils.get_uid(), id):
        return "0"
    else:
        return "-1"

@translate_blueprint.route('/get/<text>')
def translate_get(text):
    translation = translators.get(user_utils.get_uid(), text)
    return translation if translation else "-1"

@translate_blueprint.route('/leave', methods=['POST'])
def translate_leave():
    translators.deattach(user_utils.get_uid())
    return "0"

@translate_blueprint.route('/file', methods=['POST'])
def upload_file():
    engine_id = request.form.get('engine_id')
    user_file = request.files.get('user_file')
    
    key = utils.normname(user_utils.get_uid(), user_file.filename)
    this_upload = user_utils.get_user_folder(key)
    os.mkdir(this_upload)
    
    user_file_path = os.path.join(this_upload, secure_filename(user_file.filename))
    user_file.save(user_file_path)

    translate_attach(engine_id)
    translators.translate_xml(user_utils.get_uid(), user_file_path)

    return key

@translate_blueprint.route('/download/<key>')
def download_file(key):
    user_upload = user_utils.get_user_folder(key)
    files = [f for f in glob.glob(os.path.join(user_upload, "*"))]
    file = os.path.join(user_upload, files[0]) if len(files) > 0 else None

    @after_this_request
    def remove_file(response):
        if file:
            shutil.rmtree(user_upload)

    if len(files) > 0:
        return send_file(os.path.join(user_upload, files[0]), as_attachment=True)
    else:
        return "-1"