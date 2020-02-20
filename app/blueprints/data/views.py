from app import app, db
from app.models import File, BilingualCorpus
from app.utils import utils, user_utils
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from random import randint
from sqlalchemy.orm.exc import NoResultFound

import os
import hashlib

data_blueprint = Blueprint('data', __name__, template_folder='templates')

@data_blueprint.route('/')
def data_index():
    return render_template('data.html.jinja2', page_name='data')

@data_blueprint.route('/upload/<type>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload(type):
    return render_template('upload.data.html.jinja2', page_name='data', type=type)

@data_blueprint.route('/upload/<type>/perform', methods=['POST'])
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def data_upload_perform(type):
    if request.method == 'POST':
        source_file = request.files.get('source_file')
        target_file = request.files.get('target_file')

        source_db_file = upload_file(source_file)
        target_db_file = upload_file(target_file)

        bilingualcorpus = BilingualCorpus(name = request.form['name'], source = source_db_file.id, target = target_db_file.id)
        db.session.add(bilingualcorpus)
        db.session.commit()

        return jsonify({ "status": "OK" })
    else:
        return jsonify({ "status": "ERR" })

def upload_file(file):
    path = os.path.join(app.config['UPLOAD_FOLDER'], '{}-{}'.format(file.filename, randint(1, 100000)))
    blake = hashlib.blake2b()

    while True:
        data = file.read(65536)
        if not data: break
        blake.update(data)

    hash = blake.hexdigest()

    query = File.query.filter_by(hash = hash)
    db_file = None
    try:
        db_file = query.one()
        os.symlink(db_file.path, path)

        db_file = File(path = path, hash = hash, owner = user_utils.get_uid())
    except NoResultFound:
        file.save(path)
        db_file = File(path = path, hash = hash, owner = user_utils.get_uid())
    finally:
        if db_file is not None:
            db.session.add(db_file)
            db.session.commit()

    return db_file