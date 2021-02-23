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

@evaluate_blueprint.route('/download/<id>/<index>')
def evaluate_download(id, index):
    task_success, task_value = utils.get_task_result(tasks.evaluate_files, id)
    index = int(index)
    if task_success:
        file_paths = task_value[1]
        return send_file(file_paths[index], as_attachment=True)
    return "Error"

@evaluate_blueprint.route('/evaluate_files', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def evaluate_files():
    mt_files = request.files.getlist('mt_files[]')
    ht_files = request.files.getlist('ht_files[]')
    source_file = request.files.get('source_file')

    line_length = None

    def save_file(file, path, limit = 500):
        with open(path, 'w') as output_file:
            for i, line in enumerate(file):
                if i < limit:
                    print(line.decode('utf-8').strip(), file=output_file)

    mt_paths = []
    for mt_file in mt_files:
        mt_path = utils.filepath('FILES_FOLDER', utils.normname(user_utils.get_uid(), mt_file.filename))
        save_file(mt_file, mt_path)

        if not line_length:
            line_length = utils.file_length(mt_path)
        elif utils.file_length(mt_path) != line_length:
            return ({ "result": "-1" })

        mt_paths.append(mt_path)

    ht_paths = []
    for ht_file in ht_files:
        ht_path = utils.filepath('FILES_FOLDER', utils.normname(user_utils.get_uid(), ht_file.filename))
        save_file(ht_file, ht_path)

        if not line_length:
            line_length = utils.file_length(ht_path)
        elif utils.file_length(ht_path) != line_length:
            return ({ "result": "-1" })

        ht_paths.append(ht_path)

    if source_file:
        source_path = utils.filepath('FILES_FOLDER', utils.normname(user_utils.get_uid(), source_file.filename))
        save_file(source_file, source_path)
    
        if utils.file_length(ht_path) != utils.file_length(source_path):
            return ({ "result": "-1" })

    task = tasks.evaluate_files.apply_async(args=[user_utils.get_uid(), mt_paths, ht_paths], kwargs={'source_path': source_path if source_file else None})
    return ({ "result": 200, "task_id": task.id })

@evaluate_blueprint.route('/get_evaluation', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_evaluation():
    task_id = request.form.get('task_id')
    task_success, task_value = utils.get_task_result(tasks.evaluate_files, task_id)
    if task_success:
        evaluation_result = task_value[0]
        return jsonify({ "result": 200, "task_id": task_id, "evaluation": evaluation_result })
    else:
        return jsonify({ "result": -1 })
