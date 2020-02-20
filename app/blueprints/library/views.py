from app import app
from flask import Blueprint, render_template

library_blueprint = Blueprint('library', __name__, template_folder='templates')

@library_blueprint.route('/')
def library_index():
    return render_template('library.html.jinja2', page_name='library')