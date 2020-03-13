from app import app
from app.models import LibraryEngine
from app.utils import user_utils, translation_utils
from flask import Blueprint, render_template, request, jsonify

inspect_blueprint = Blueprint('inspect', __name__, template_folder='templates')

translators = translation_utils.TranslationUtils()

@inspect_blueprint.route('/')
def inspect_index():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()).all()
    return render_template('inspect.html.jinja2', page_name='inspect', engines=engines)

@inspect_blueprint.route('/leave', methods=['POST'])
def translate_leave():
    translators.deattach(user_utils.get_uid())
    return "0"

@inspect_blueprint.route('/attach_engine/<id>')
def translate_attach(id):
    if translators.launch(user_utils.get_uid(), id, True):
        return "0"
    else:
        return "-1"

@inspect_blueprint.route('/get/<text>')
def inspect_get(text):
    translation = translators.get_inspect(user_utils.get_uid(), text)
    return jsonify(translation) if translation else "-1"