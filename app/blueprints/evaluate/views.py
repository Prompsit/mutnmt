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
    mt_files = request.files.getlist('mt_files[]')
    ht_file = request.files.get('ht_file')
    source_file = request.files.get('source_file')
    
    ht_path = utils.filepath('FILES_FOLDER', utils.normname(user_utils.get_uid(), ht_file.filename))
    ht_file.save(ht_path)

    line_length = utils.file_length(ht_path)

    mt_paths = []
    for mt_file in mt_files:
        mt_path = utils.filepath('FILES_FOLDER', utils.normname(user_utils.get_uid(), mt_file.filename))
        mt_file.save(mt_path)

        if utils.file_length(ht_path) != line_length:
            return ({ "result": "-1" })

        mt_paths.append(mt_path)

    if source_file:
        source_path = utils.filepath('FILES_FOLDER', utils.normname(user_utils.get_uid(), source_file.filename))
        source_file.save(source_path)
    
        if utils.file_length(ht_path) != utils.file_length(source_path):
            return ({ "result": "-1" })

    task = tasks.evaluate_files.apply_async(args=[user_utils.get_uid(), mt_paths, ht_path], kwargs={'source_path': source_path if source_file else None})
    return ({ "result": 200, "task_id": task.id })

@evaluate_blueprint.route('/get_evaluation', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def get_evaluation():
    task_id = request.form.get('task_id')
    task_result = utils.get_task_result(tasks.evaluate_files, task_id)
    if task_result:
        return jsonify({ "result": 200, "evaluation": task_result })
    else:
        return jsonify({ "result": -1 })
