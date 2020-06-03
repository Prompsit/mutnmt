from app import app
from .evaluator import Evaluator
from app.utils import user_utils, utils, tasks
from flask import Blueprint, render_template, request, jsonify, url_for, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename
import pyter
import xlsxwriter

import os
import pkgutil
import importlib
import inspect
import subprocess
import sys
import re

evaluate_blueprint = Blueprint('evaluate', __name__, template_folder='templates')

@evaluate_blueprint.route('/', methods=["GET", "POST"])
def evaluate_index():
    return render_template('evaluate.html.jinja2', page_name='evaluate', page_title='Evaluate')

@evaluate_blueprint.route('/download/<name>')
def evaluate_download(name):
    task_result = utils.get_task_result(tasks.evaluate_files, name)
    return send_file(task_result['xlsx_url'], as_attachment=True)

@evaluate_blueprint.route('/evaluate_files', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def evaluate_files():
    mt_file = request.files.get('mt_file')
    ht_file = request.files.get('ht_file')

    def get_normname(file):
        return secure_filename('{}-{}'.format(user_utils.get_user().username, file.filename))
    
    mt_path = os.path.join(app.config['FILES_FOLDER'], get_normname(mt_file))
    ht_path = os.path.join(app.config['FILES_FOLDER'], get_normname(ht_file))

    mt_file.save(mt_path)
    ht_file.save(ht_path)

    if utils.file_length(mt_path) != utils.file_length(ht_path):
        return ({ "result": "-1" })

    task = tasks.evaluate_files.apply_async(args=[user_utils.get_uid(), mt_path, ht_path])
    return task.id

@evaluate_blueprint.route('/get_evaluation', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_evaluation():
    task_id = request.form.get('task_id')
    task_result = utils.get_task_result(tasks.evaluate_files, task_id)
    if task_result:
        return jsonify({ "result": 200, "evaluation": task_result })
    else:
        return jsonify({ "result": -1 })
