from app import app, db
from app.models import User, File, LibraryCorpora, LibraryEngine, Resource, Engine, Corpus, Corpus_File, LibraryEngine, Language, Corpus_Engine
from app.utils import user_utils, utils, datatables, tensor_utils
from app.flash import Flash
from flask_login import login_required
from sqlalchemy import and_, not_
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, send_file
from datetime import datetime
from dateutil import tz
from functools import reduce

import os
import hashlib
import sys
import shutil
import pytz
import ntpath
import re

library_blueprint = Blueprint('library', __name__, template_folder='templates')

@library_blueprint.route('/corpora')
def library_corpora():
    user_library = Corpus.query.filter_by(owner_id = user_utils.get_uid()).all()
    public_files = Corpus.query.filter(and_(Corpus.public == True, Corpus.owner_id != user_utils.get_uid()))
    languages = Language.query.all()

    return render_template('library_corpora.html.jinja2', page_name = 'library_corpora', page_title = 'Corpora',
            user_library = user_library, public_files = public_files, languages=languages)

@library_blueprint.route('/engines')
def library_engines():
    user_library = User.query.filter_by(id = user_utils.get_uid()).first().user_engines
    public_engines = Engine.query.filter_by(public = True)

    user_engines = list(map(lambda l : l.engine, user_library))
    for engine in public_engines:
        engine.grabbed = engine in user_engines

    return render_template('library_engines.html.jinja2', page_name = 'library_engines', page_title = 'Engines',
            user_library = user_library, public_engines = public_engines)

@library_blueprint.route('/engine/<int:id>')
def library_engine(id):
    engine = Engine.query.filter_by(id=id).first()
    corpora = Corpus_Engine.query.filter_by(engine_id=id, is_info=True).all()

    training_regex = r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2},\d+)\s+Epoch\s+1\s+Step:\s+(\d+)\s+Batch Loss:\s+(\d+\.\d+)\s+Tokens per sec:\s+(\d+),\s+Lr:\s+(\d+\.\d+)$'
    validation_regex = r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2},\d+)\s(\w|\s|\(|\))+(\d+),\s+step\s*(\d+):\s+bleu:\s+(\d+\.\d+),\s+loss:\s+(\d+\.\d+),\s+ppl:\s+(\d+\.\d+),\s+duration:\s+(\d+.\d+)s$'
    re_flags = re.IGNORECASE | re.UNICODE

    score = 0.0
    tps = []
    with open(os.path.join(engine.path, "model/train.log"), 'r') as log_file:
        first_time, last_time = None, None

        for line in log_file:
            groups = re.search(training_regex, line, flags=re_flags)
            if groups:
                if not first_time: first_time = "{} {}".format(groups[1], groups[2])
                last_time = "{} {}".format(groups[1], groups[2])
                tps.append(float(groups[5]))
            else:
                # It was not a training line, could be validation
                groups = re.search(validation_regex, line, flags=re_flags)
                if groups:
                    bleu_score = float(groups[6])
                    score = bleu_score if bleu_score > score else score

    if len(tps) > 0:
        tps_value = reduce(lambda a, b: a + b, tps)
        tps_value = round(tps_value / len(tps))
    else:
        tps_value = "—"
    
    if first_time and last_time:
        first_datetime = datetime.strptime(first_time, '%Y-%m-%d %H:%M:%S,%f')
        last_datetime = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S,%f')
        time_elapsed = (last_datetime - first_datetime)
        time_elapsed_format = "{}d {}h {}m {}s".format(time_elapsed.days, 
                                round(time_elapsed.seconds / 3600), round((time_elapsed.seconds % 3600) / 60), round(time_elapsed.seconds % 60))
    else:
        time_elapsed_format = "—"
    
    return render_template('library_engine_details.html.jinja2', page_name = 'library_engines_detail',
            page_title = 'Engine details', engine = engine, corpora = corpora, score = score, tps = tps_value, 
            time_elapsed = time_elapsed_format)

@library_blueprint.route('/corpora_feed', methods=["POST"])
def library_corpora_feed():
    public = request.form.get('public') == "true"

    user_library =  Corpus.query.filter(and_(Corpus.public == True, Corpus.owner_id != user_utils.get_uid(), Corpus.visible == True)) if public \
                        else Corpus.query.filter_by(owner_id = user_utils.get_uid(), visible = True).all()

    dt = datatables.Datatables(draw=int(request.form.get('draw')))
    rows, rows_filtered, search = [], [], None

    corpus_data = []
    for corpus in user_library:
        columns = [File.id, File.name, File.language_id, File.lines, File.words, File.chars, File.uploaded]

        rows, rows_filtered, search = dt.parse(File, columns, request, File.corpora.any(Corpus_File.corpus_id == corpus.id))

        for file in (rows_filtered if search else rows):
            uploaded_date = datetime.fromtimestamp(datetime.timestamp(file.uploaded)).strftime("%d/%m/%Y %H:%M:%S")
            corpus_data.append([file.id, file.name, file.language.name, file.lines, file.words, file.chars, uploaded_date, "",
                                {
                                    "corpus_owner": file.uploader.id == user_utils.get_uid() if file.uploader else False,
                                    "corpus_id": corpus.id,
                                    "corpus_name": corpus.name,
                                    "corpus_description": corpus.description,
                                    "corpus_source": corpus.source.name,
                                    "corpus_target": corpus.target.name if corpus.target else "",
                                    "corpus_public": corpus.public,
                                    "corpus_preview": url_for('library.corpora_preview', id = corpus.id),
                                    "corpus_share": url_for('library.library_share_toggle', type = 'library_corpora', id = corpus.id),
                                    "corpus_delete": url_for('library.library_delete', id = corpus.id, type = 'library_corpora'),
                                    "corpus_grab": url_for('library.library_grab', id = corpus.id, type = 'library_corpora'),
                                    "corpus_ungrab": url_for('library.library_ungrab', id = corpus.id, type = 'library_corpora'),
                                    "corpus_export": url_for('library.library_export', id= corpus.id, type = "library_corpora"),
                                    "file_preview": url_for('data.data_preview', file_id=file.id)
                                }])

    return dt.response(rows, rows_filtered, corpus_data)

@library_blueprint.route('/engines_feed', methods=["POST"])
def library_engines_feed():
    public = request.form.get('public') == "true"
    columns = [Engine.id, Engine.name, Engine.description, Engine.source_id, Engine.target_id, Engine.uploaded]
    dt = datatables.Datatables()

    rows, rows_filtered, search = dt.parse(Engine, columns, request, 
                                    and_(Engine.public == True, not_(Engine.engine_users.any(LibraryEngine.user_id == user_utils.get_uid()))) if public 
                                    else Engine.engine_users.any(LibraryEngine.user_id == user_utils.get_uid()))

    engine_data = []
    for engine in (rows_filtered if search else rows):
        uploaded_date = datetime.fromtimestamp(datetime.timestamp(engine.uploaded)).strftime("%d/%m/%Y %H:%M:%S")
        engine_data.append([engine.id, engine.name, engine.description, "{} — {}".format(engine.source.name, engine.target.name),
                            uploaded_date, engine.uploader.username if engine.uploader else "", "",
                            {
                                "engine_owner": engine.uploader.id == user_utils.get_uid() if engine.uploader else False,
                                "engine_public": engine.public,
                                "engine_share": url_for('library.library_share_toggle', type = "library_engines", id = engine.id),
                                "engine_detail": url_for('library.library_engine', id = engine.id),
                                "engine_summary": url_for('train.train_console', id = engine.id),
                                "engine_delete": url_for('library.library_delete', id = engine.id, type = "library_engines"),
                                "engine_grab": url_for('library.library_grab', id = engine.id, type = "library_engines"),
                                "engine_ungrab": url_for('library.library_ungrab', id = engine.id, type = "library_engines"),
                                "engine_export": url_for('library.library_export', id= engine.id, type = "library_engines")
                            }])

    return dt.response(rows, rows_filtered, engine_data)

@library_blueprint.route('/preview/<id>')
def corpora_preview(id):
    try:
        corpus = Corpus.query.filter_by(id = id).first()
        return render_template('library_preview.html.jinja2', page_name = 'library_preview',
                corpus=corpus)
    except:
        Flash.issue("Preview is currently unavailable", Flash.ERROR)
        return render_template(request.referrer)

@library_blueprint.route('/stream', methods=["POST"])
def stream_file():
    file_id = request.form.get('file_id')

    try:
        start = int(request.form.get('start'))
        offset = int(request.form.get('offset'))

        file = File.query.filter_by(id=file_id).first()
        lines = [line for line in utils.file_reader(file.path, start, offset)]
        return jsonify({ "result": 200, "lines": lines })
    except:
        return jsonify({ "result": -1, "lines": [] })

@library_blueprint.route('/share/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_share_toggle(type, id):
    if type == "library_corpora":
        db_resource = Corpus.query.filter_by(owner_id = user_utils.get_uid(), id = id).first()
        db_resource.public = not db_resource.public
        db.session.commit()
    else:
        db_resource = Engine.query.filter_by(uploader_id = user_utils.get_uid(), id = id).first()
        db_resource.public = not db_resource.public
        db.session.commit()

    return redirect(request.referrer)

@library_blueprint.route('/grab/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_grab(type, id):
    user = User.query.filter_by(id = user_utils.get_uid()).first()

    if type == "library_corpora":
        corpus = Corpus.query.filter_by(id = id).first()
        user.user_corpora.append(LibraryCorpora(corpus=corpus, user=user))
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

    return redirect(request.referrer)

@library_blueprint.route('/delete/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_delete(type, id):
    user_utils.library_delete(type, id)

    return redirect(request.referrer)

@library_blueprint.route('/export/<type>/<id>')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def library_export(type, id):
    zip_path = None

    if type == 'library_engines':
        engine = Engine.query.filter_by(id=id).first()
        zip_path = os.path.join(app.config['TMP_FOLDER'], 'engine-{}.mut'.format(engine.id))
        shutil.make_archive(zip_path, 'zip', engine.path, '.')
    else:
        tmp_folder = utils.tmpfolder()
        corpus = Corpus.query.filter_by(id=id).first()
        for file_entry in corpus.corpus_files:
            filename = ntpath.basename(file_entry.file.path)
            shutil.copy(file_entry.file.path, os.path.join(tmp_folder, file_entry.file.name))
        zip_path = os.path.join(app.config['TMP_FOLDER'], 'corpus-{}.mut.zip'.format(corpus.id))
        shutil.make_archive(zip_path, 'zip', tmp_folder, '.')
        shutil.rmtree(tmp_folder)

    return send_file(zip_path + '.zip', as_attachment=True)
