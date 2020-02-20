from app import app
from flask import Blueprint, render_template

inspect_blueprint = Blueprint('inspect', __name__, template_folder='templates')

@inspect_blueprint.route('/')
def inspect_index():
    return render_template('inspect.html.jinja2', page_name='inspect')