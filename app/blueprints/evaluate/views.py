from app import app
from .evaluator import Evaluator
from app.utils import user_utils, utils
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
    file_path = utils.tmpfile(name)
    return send_file(file_path)

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

    if utils.file_length(mt_path) != utils.file_length(ht_path):
        return ({ "result": "-1" })


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
        #try:
        metrics.append({
            "name": evaluator.get_name(),
            "value": evaluator.get_value(mt_path, ht_path)
        })
        #except:
        #    pass

    spl_result, xlsx_name = spl(mt_path, ht_path)
    os.remove(mt_path)
    try:
        os.remove(ht_path)
    except FileNotFoundError:
        # It was the same file, we just pass
        pass

    return jsonify({ "result": 200, "metrics": metrics, "spl": spl_result, "xlsx_url": url_for('evaluate.evaluate_download', name=xlsx_name) })

def spl(mt_path, ht_path):
    # Scores per line (bleu and ter)
    sacreBLEU = subprocess.Popen("cat {} | sacrebleu -sl -b {} > {}.bpl".format(mt_path, ht_path, mt_path), 
                        cwd=app.config['MUTNMT_FOLDER'], shell=True, stdout=subprocess.PIPE)
    sacreBLEU.wait()

    bpl_result = subprocess.Popen("paste {} {} {}.bpl".format(mt_path, ht_path, mt_path), shell=True, stdout=subprocess.PIPE)

    line_number = 1
    per_line = []
    for line in bpl_result.stdout:
        line = line.decode("utf-8")
        per_line.append([line_number] + [i.strip() for i in re.split(r'\t', line)])
        line_number += 1

    os.remove("{}.bpl".format(mt_path))

    rows = []
    for row in per_line:
        ht_line = row[2].strip()
        mt_line = row[1].strip()
        if ht_line and mt_line:
            ter = round(pyter.ter(ht_line.split(), mt_line.split()), 2)
            rows.append(row + [100 if ter > 1 else (ter * 100)])

    xlsx_name = generate_xlsx(rows)

    return rows, xlsx_name

def generate_xlsx(rows):
    file_name = utils.normname(user_utils.get_uid(), "evaluation") + ".xlsx"
    file_path = utils.tmpfile(file_name)

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    rows = [["Line", "Machine translation", "Human translation", "Bleu", "TER"]] + rows

    row_cursor = 0
    for row in rows:
        for col_cursor, col in enumerate(row):
            worksheet.write(row_cursor, col_cursor, col)
        row_cursor  += 1

    workbook.close()

    return file_name