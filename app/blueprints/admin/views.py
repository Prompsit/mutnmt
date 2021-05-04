from app.models import User, Corpus, Engine, RunningEngines
from app.utils import user_utils, utils, datatables
from app.utils.trainer import Trainer
from app import db, app
from flask import Blueprint, render_template, request, jsonify, redirect, escape, url_for
from flask_login import login_required

import shutil
import psutil
import pynvml
import subprocess

admin_blueprint = Blueprint('admin', __name__, template_folder='templates')

@admin_blueprint.route('/')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def admin_index():
    if user_utils.is_normal(): return redirect(url_for('index'))

    return render_template('users.admin.html.jinja2', page_name='admin_users', page_title='Users')

@admin_blueprint.route('/user/<id>', methods=['GET', 'POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def user_edit(id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    user = User.query.filter_by(id=id).one()
    if request.method == 'GET':
        return render_template('users_edit.admin.html.jinja2', page_name='admin_users', page_title='Edit user',
                               user=user)
    else:
        notes = request.form.get('userNotes')
        user.notes = escape(notes)
        db.session.commit()
        return redirect(request.referrer)

@admin_blueprint.route('/system')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def admin_system():
    if user_utils.is_normal(): return redirect(url_for('index'))

    factor = 1073741824
    vmem = psutil.virtual_memory()
    ram = { "percent": vmem.percent, "used": round(vmem.used / factor, 2), "total": round(vmem.total / factor, 2) } # GB
    
    hdd = psutil.disk_usage(app.config['USERSPACE_FOLDER'])
    disk_usage = { "percent": round((hdd.used / hdd.total) * 100, 2), "used": round(hdd.used / factor, 2), 
                    "total": round(hdd.total / factor, 2)} # GB
    
    gpus = []
    pynvml.nvmlInit()
    for i in range(0, pynvml.nvmlDeviceGetCount()):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        resources = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpus.append({ "id": i, 
                        "memory": resources.memory,
                        "proc": resources.gpu
                    })

    return render_template('system.admin.html.jinja2', page_name='admin_system', page_title='System',
                            ram=ram, cpu=round(psutil.cpu_percent(), 2), gpus=gpus,
                            disk_usage=disk_usage)


@admin_blueprint.route('/instances')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def admin_instances():
    if user_utils.is_normal(): return redirect(url_for('index'))

    return render_template('instances.admin.html.jinja2', page_name='admin_instances', page_title='Instances')

@admin_blueprint.route('/users_feed', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def user_datatables_feed():
    if user_utils.is_normal(): return redirect(url_for('index'))

    columns = [User.id, User.username, User.email, User.notes]
    dt = datatables.Datatables()

    rows, rows_filtered, search = dt.parse(User, columns, request)

    user_data = []
    for user in (rows_filtered if search else rows):
        user_data.append([user.id, user.username, user.email,
                          'Admin' if user.admin else 'Expert' if user.expert else 'Beginner',
                          user.notes, '',
                          user.admin, user.expert])

    return dt.response(rows, rows_filtered, user_data)

@admin_blueprint.route('/python_feed', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def python_feed():
    if user_utils.is_normal(): return redirect(url_for('index'))

    draw = request.form.get('draw')
    search = request.form.get('search[value]')
    start = int(request.form.get('start'))
    length = int(request.form.get('length'))
    order = int(request.form.get('order[0][column]'))
    dir = request.form.get('order[0][dir]')

    ps = subprocess.Popen("ps aux | grep python", shell=True, stdout=subprocess.PIPE)
    ps.wait()

    rows = []
    for line_raw in ps.stdout:
        line = line_raw.decode("utf-8").strip()
        if line:
            data = line.split(None)
            command = " ".join(data[10:])
            if not any(x in command for x in ["ps aux", "grep python", "<defunct>"]):
                rows.append([data[1], data[8], data[2], data[3], command])

    if start and length:
        rows = rows[start:length]

    if order is not None:
        rows.sort(key=lambda row: row[order], reverse=(dir == "desc"))

    rows_filtered = []
    if search:
        for row in rows:
            found = False

            for col in row:
                if not found:
                    if search in col:
                        rows_filtered.append(row)
                        found = True

    return jsonify({
        "draw": int(draw) + 1,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows_filtered) if search else len(rows),
        "data": rows_filtered if search else rows
    })


@admin_blueprint.route('/instances_feed', methods=["POST"])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def instances_datatables_feed():
    if user_utils.is_normal(): return redirect(url_for('index'))

    columns = [Engine.id, Engine.name]
    dt = datatables.Datatables()

    rows, rows_filtered, search = dt.parse(Engine, columns, request, Engine.status.like("training"))

    user_data = []
    for engine in (rows_filtered if search else rows):
        user_data.append([engine.id, engine.name, engine.uploader.email if engine.uploader else "", "Training", None])

    columns_translating = [RunningEngines.id]
    rows_translating, rows_translating_filtered, search_translating = dt.parse(RunningEngines, columns_translating, request)

    for engine_entry in (rows_translating_filtered if search_translating else rows_translating):
        user_data.append([engine_entry.engine.id, engine_entry.engine.name, 
                            engine_entry.engine.uploader.email if engine_entry.engine.uploader else "", 
                            "Translating", None])

    return dt.response(rows, rows_filtered, user_data)

@admin_blueprint.route('/delete_user')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def delete_user():
    if user_utils.is_normal(): return redirect(url_for('index'))

    id = request.args.get('id')

    try:
        assert int(id) != user_utils.get_uid()
        user = User.query.filter_by(id = id).first()
        for corpus in Corpus.query.filter_by(owner_id = id).all():
            user_utils.library_delete("library_corpora", corpus.id, id)

        for engine_entry in user.user_engines:
            user_utils.library_delete("library_engines", engine_entry.engine.id, id)

        shutil.rmtree(user_utils.get_user_folder(user_id=id))
        db.session.delete(user)
        db.session.commit()
    except:
        pass

    return redirect(request.referrer)

@admin_blueprint.route('/stop_engine')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def stop_engine():
    if user_utils.is_normal(): return redirect(url_for('index'))

    id = request.args.get('id')

    try:
        Trainer.stop(id, admin_stop=True)
    except:
        pass

    return redirect(request.referrer)

@admin_blueprint.route('/become/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def become(type, id):
    if user_utils.is_normal(): return redirect(url_for('index'))

    if user_utils.get_user().admin:
        user = User.query.filter_by(id = id).first()

        user.expert = (type == "expert")
        user.admin = (type == "admin")
        user.normal = (type == "normal")

        db.session.commit()

    return redirect(request.referrer)