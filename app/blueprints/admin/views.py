from app.models import User, Corpus
from app.utils import user_utils, utils, datatables
from app import db
from flask import Blueprint, render_template, request, jsonify, redirect
from flask_login import login_required

import shutil
import psutil
import nvidia_smi

admin_blueprint = Blueprint('admin', __name__, template_folder='templates')

@admin_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def admin_index():
    return render_template('users.admin.html.jinja2', page_name='admin_users')

@admin_blueprint.route('/system')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def admin_system():
    factor = 1073741824
    vmem = psutil.virtual_memory()
    ram = { "percent": vmem.percent, "used": round(vmem.used / factor, 2), "total": round(vmem.total / factor, 2) }

    gpus = []
    nvidia_smi.nvmlInit()
    for i in range(0, nvidia_smi.nvmlDeviceGetCount()):
        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(i)
        resources = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
        gpus.append({ "id": i, 
                        "memory": resources.memory,
                        "proc": resources.gpu
                    })

    return render_template('system.admin.html.jinja2', page_name='admin_system', 
                            ram=ram, cpu=round(psutil.cpu_percent(), 2), gpus=gpus)

@admin_blueprint.route('/users_feed', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def user_datatables_feed():
    columns = [User.id, User.username, User.email]
    dt = datatables.Datatables()

    rows, rows_filtered, search = dt.parse(User, columns, request)

    user_data = []
    for user in (rows_filtered if search else rows):
        user_data.append([user.id, user.username, user.email,
                        "Admin" if user.admin else "Expert" if user.expert else "Normal", 
                        "", user.admin, user.expert])

    return dt.response(rows, rows_filtered, user_data)

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