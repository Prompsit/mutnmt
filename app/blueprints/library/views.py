from app import app
from app.models import File
from app.utils import user_utils

from flask import Blueprint, render_template

library_blueprint = Blueprint('library', __name__, template_folder='templates')

@library_blueprint.route('/')
def library_index():
    files = File.query.filter_by(uploader_id=user_utils.get_uid()).all()
    return render_template('library.html.jinja2', page_name='library', files=files)