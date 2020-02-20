from app import app
from flask import Blueprint, render_template

data_blueprint = Blueprint('data', __name__, template_folder='templates')

@data_blueprint.route('/')
def data_index():
    return render_template('data.html.jinja2')