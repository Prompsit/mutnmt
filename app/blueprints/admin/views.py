from app.models import User, Corpus
from app.utils import user_utils, utils
from app import db
from flask import Blueprint, render_template, request, jsonify, redirect
from sqlalchemy.orm import load_only
from flask_login import login_required

import shutil

admin_blueprint = Blueprint('admin', __name__, template_folder='templates')

@admin_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def admin_index():
    return render_template('users.admin.html.jinja2', page_name='admin_users')

@admin_blueprint.route('/users_feed', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def user_datatables_feed():
    draw = request.form.get('draw')
    start = request.form.get('start')
    length = request.form.get('length')
    
    columns = [User.id, User.username, User.email]
    
    users = User.query.options(load_only(*columns)).limit(length).offset(start).all()
    user_data = []
    for user in users:
        user_data.append([user.id, user.username, user.email, "", user.admin, user.expert])

    return jsonify({
        "draw": int(draw) + 1,
        "recordsTotal": len(users),
        "recordsFiltered": len(users),
        "data": user_data
    })

@admin_blueprint.route('/delete_user')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def delete_user():
    id = request.args.get('id')

    try:
        assert int(id) != user_utils.get_uid()
        user = User.query.filter_by(id = id).first()
        for corpus in Corpus.query.filter_by(owner_id = id).all():
            user_utils.library_delete("library_corpora", corpus.id, id)

        for engine_entry in user.user_engines:
            user_utils.library_delete("library_engines", engine_entry.engine.id, id)

        shutil.rmtree(user_utils.get_user_folder())
        db.session.delete(user)
        db.session.commit()
    except:
        pass

    return redirect(request.referrer)

@admin_blueprint.route('/become/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def become(type, id):
    if user_utils.get_user().admin:
        user = User.query.filter_by(id = id).first()

        user.expert = (type == "expert")
        user.admin = (type == "admin")
        user.normal = (type == "normal")

        db.session.commit()

    return redirect(request.referrer)