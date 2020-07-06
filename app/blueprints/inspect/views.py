from app import app
from app.models import LibraryEngine, Engine
from app.utils import user_utils
from app.utils.translation.utils import TranslationUtils
from app.utils import tasks
from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import or_

inspect_blueprint = Blueprint('inspect', __name__, template_folder='templates')

translators = TranslationUtils()

@inspect_blueprint.route('/')
@inspect_blueprint.route('/details')
def inspect_index():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()) \
            .join(Engine, LibraryEngine.engine) \
            .filter(or_(Engine.status == "stopped", Engine.status == "finished")) \
            .order_by(Engine.uploaded.desc()) \
            .all()
    return render_template('details.inspect.html.jinja2', page_name='inspect_details', page_title='Details', engines=engines)

@inspect_blueprint.route('/compare')
def inspect_compare():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()) \
            .join(Engine, LibraryEngine.engine) \
            .filter(or_(Engine.status == "stopped", Engine.status == "finished")) \
            .order_by(Engine.uploaded.desc()) \
            .all()
    return render_template('compare.inspect.html.jinja2', page_name='inspect_compare', page_title='Compare', engines=engines)

@inspect_blueprint.route('/access')
def inspect_access():
    engines = LibraryEngine.query.filter_by(user_id = user_utils.get_uid()) \
            .join(Engine, LibraryEngine.engine) \
            .filter(or_(Engine.status == "stopped", Engine.status == "finished")) \
            .order_by(Engine.uploaded.desc()) \
            .all()
    return render_template('access.inspect.html.jinja2', page_name='inspect_access', page_title='Access', engines=engines)

@inspect_blueprint.route('/leave', methods=['POST'])
def translate_leave():
    translators.deattach(user_utils.get_uid())
    return "0"

@inspect_blueprint.route('/details', methods=["POST"])
def inspect_details():
    line = request.form.get('line')
    engine_id = request.form.get('engine_id')
    translation_task_id = translators.get_inspect(user_utils.get_uid(), engine_id, line)

    return translation_task_id

@inspect_blueprint.route('/get_details', methods=["POST"])
def get_inspect_details():
    task_id = request.form.get('task_id')
    result = tasks.translate_text.AsyncResult(task_id)
    if result and result.status == "SUCCESS":
        return jsonify({ "result": 200, "details": result.get() })
    else:
        return jsonify({ "result": -1 })

@inspect_blueprint.route('/compare/text', methods=["POST"])
def inspect_compare_text():
    text = request.form.get('text')
    engines = request.form.getlist('engines[]')
    task_id = tasks.inspect_compare.apply_async(args=[user_utils.get_uid(), engines, text]).id
    return task_id

@inspect_blueprint.route('/get_compare', methods=["POST"])
def inspect_get_compare():
    task_id = request.form.get('task_id')
    result = tasks.translate_text.AsyncResult(task_id)
    if result and result.status == "SUCCESS":
        return jsonify({ "result": 200, "compare": result.get() })
    else:
        return jsonify({ "result": -1 })