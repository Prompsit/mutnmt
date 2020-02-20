from app import app
from flask import Blueprint, render_template

train_blueprint = Blueprint('train', __name__, template_folder='templates')

@train_blueprint.route('/')
def train_index():
    return render_template('train.html.jinja2')