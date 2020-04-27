from app import app
from .evaluator import Evaluator
from app.utils import user_utils, utils
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from werkzeug.utils import secure_filename

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
    return render_template('evaluate.html.jinja2', page_name='evaluate')

@evaluate_blueprint.route('/perform', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def evaluate_perform():
    mt_file = request.files.get('mt_file')
    ht_file = request.files.get('ht_file')

    def get_normname(file):
        return secure_filename('{}-{}'.format(user_utils.get_user().username, file.filename))
    
    mt_path = os.path.join(app.config['FILES_FOLDER'], get_normname(mt_file))
    ht_path = os.path.join(app.config['FILES_FOLDER'], get_normname(ht_file))

    mt_file.save(mt_path)
    ht_file.save(ht_path)

    # Load evaluators from ./evaluators folder
    evaluators: Evaluator = []
    for minfo in pkgutil.iter_modules([os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluators")]):
        module = importlib.import_module('.{}'.format(minfo.name), package='app.blueprints.evaluate.evaluators')
        classes = inspect.getmembers(module)
        for name, _class in classes:
            if name != "Evaluator" and name.lower() == minfo.name.lower() and inspect.isclass(_class):
                evaluator = getattr(module, name)
                evaluators.append(evaluator())

    metrics = []
    for evaluator in evaluators:
        try:
            metrics.append({
                "name": evaluator.get_name(),
                "value": evaluator.get_value(mt_path, ht_path)
            })
        except:
            pass

    bpl_result = bpl(mt_path, ht_path)

    os.remove(mt_path)
    os.remove(ht_path)

    return jsonify({ "metrics": metrics, "bpl": bpl_result })

def bpl(mt_path, ht_path):
    sacreBLEU = subprocess.Popen("cat {} | sacrebleu -sl -b {} > {}.bpl".format(mt_path, ht_path, mt_path), 
                        cwd=app.config['MUTNMT_FOLDER'], shell=True, stdout=subprocess.PIPE)
    sacreBLEU.wait()

    bpl_result = subprocess.Popen("paste {} {} {}.bpl".format(mt_path, ht_path, mt_path), shell=True, stdout=subprocess.PIPE)

    line_number = 1
    per_line = []
    for line in bpl_result.stdout:
        line = line.decode("utf-8")
        per_line.append([line_number] + re.split(r'\t', line))
        line_number += 1

    os.remove("{}.bpl".format(mt_path))

    return per_line