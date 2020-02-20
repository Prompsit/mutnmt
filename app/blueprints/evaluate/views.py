from app import app
from flask import Blueprint, render_template

evaluate_blueprint = Blueprint('evaluate', __name__, template_folder='templates')

@evaluate_blueprint.route('/')
def evaluate_index():
    return render_template('evaluate.html.jinja2', page_name='evaluate')