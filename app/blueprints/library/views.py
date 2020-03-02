from app import app, db
from app.models import User, File, LibraryCorpora, LibraryEngine, Resource, Engine
from app.utils import user_utils, utils
from flask_login import login_required

from flask import Blueprint, render_template, redirect, url_for, request

import os
import hashlib
import sys

library_blueprint = Blueprint('library', __name__, template_folder='templates')

@library_blueprint.route('/')
@library_blueprint.route('/corpora')
def library_index():
    user_files = User.query.filter_by(id = user_utils.get_uid()).first().user_files
    public_files = File.query.filter_by(public = True)

    return render_template('library_corpora.html.jinja2', page_name = 'library_corpora', 
            user_files = user_files, public_files = public_files)

@library_blueprint.route('/engines')
def library_engines():
    user_engines = User.query.filter_by(id = user_utils.get_uid()).first().user_engines
    public_engines = Engine.query.filter_by(public = True)

    print("engines", file=sys.stderr)
    for engine in user_engines:
        print(engine, file=sys.stderr)

    return render_template('library_engines.html.jinja2', page_name = 'library_engines', 
            user_engines = user_engines, public_engines = public_engines)

@library_blueprint.route('/share/<id>/toggle')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_share_toggle(id):
    db_resource = Resource.query.filter_by(uploader_id = user_utils.get_uid(), id = id).first()
    db_resource.public = not db_resource.public
    db.session.commit()

    return redirect(url_for('library.library_index'))

@library_blueprint.route('/grab/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_grab(type, id):
    user = User.query.filter_by(id = user_utils.get_uid()).first()

    if type == "library_corpora":
        file = File.query.filter_by(id = id).first()
        user.user_files.append(LibraryCorpora(file=file, user=user))
    else:
        engine = Engine.query.filter_by(id = id).first()
        user.user_engines.append(LibraryEngine(engine=engine, user=user))

    db.session.commit()

    return redirect(request.referrer)

@library_blueprint.route('/remove/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_ungrab(type, id):
    user = User.query.filter_by(id = user_utils.get_uid()).first()

    if type == "library_corpora":
        library = LibraryCorpora.query.filter_by(file_id = id, user_id = user_utils.get_uid()).first()
        user.user_files.remove(library)
    else:
        library = LibraryEngine.query.filter_by(engine_id = id, user_id = user_utils.get_uid()).first()
        user.user_engines.remove(library)

    db.session.commit()

    return redirect(url_for('library.library_index'))

@library_blueprint.route('/delete/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_delete(type, id):
    user = User.query.filter_by(id = user_utils.get_uid()).first()

    if type == "library_corpora":
        library = LibraryCorpora.query.filter_by(id = id).first()
        os.remove(library.file.path)
        
        db.session.delete(library.file)
        db.session.commit()

    return redirect(url_for('library.library_index'))