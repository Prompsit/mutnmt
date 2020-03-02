from app import app
from app.models import LibraryEngine, Engine
from app.utils import user_utils
from flask import Blueprint, render_template

from toolwrapper import ToolWrapper

import subprocess, sys, logging, os

translate_blueprint = Blueprint('translate', __name__, template_folder='templates')
        
running_joey = {}

@translate_blueprint.route('/')
def translate_index():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()).all()
    return render_template('translate.html.jinja2', page_name='translate', engines = engines)

@translate_blueprint.route('/attach_engine/<id>')
def translate_attach(id):
    if user_utils.get_uid() in running_joey.keys():
        running_joey[user_utils.get_uid()].close()

    engine = Engine.query.filter_by(id = id).first()
    slave = ToolWrapper(["python3", "-m", "joeynmt", "translate", os.path.join(engine.path, "config.yaml"), "-sm"],
                        cwd=app.config['JOEYNMT_FOLDER'])

    welcome = slave.readline()
    if welcome == "!:SLAVE_READY":
        running_joey[user_utils.get_uid()] = slave
        return "0"

    return "-1"

@translate_blueprint.route('/get/<text>')
def translate_get(text):
    if user_utils.get_uid() in running_joey.keys():
        joey = running_joey[user_utils.get_uid()]
        joey.writeline(text)
        return joey.readline()
    else:
        return "-1"

@translate_blueprint.route('/leave', methods=['POST'])
def translate_leave():
    if user_utils.get_uid() in running_joey.keys():
        running_joey[user_utils.get_uid()].close()
        del running_joey[user_utils.get_uid()]
    return ""