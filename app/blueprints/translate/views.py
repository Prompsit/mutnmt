from app import app
from flask import Blueprint, render_template

translate_blueprint = Blueprint('translate', __name__, template_folder='templates')

@translate_blueprint.route('/')
def translate_index():
    return render_template('translate.html.jinja2', page_name='translate')