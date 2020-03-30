from flask_login import current_user
from app import app, db
from app.models import Corpus, LibraryEngine
import os, shutil

def get_uid():
    if isUserLoginEnabled() and current_user.is_authenticated:
        return current_user.id
    return None

def get_user():
    if isUserLoginEnabled() and current_user and current_user.get_id() != None:
        return current_user
    else:
        return None

def isUserLoginEnabled():
    return app.config["USER_LOGIN_ENABLED"] if "USER_LOGIN_ENABLED" in app.config else False

def is_admin():
    user = get_user()
    return user.admin if user else False

def is_expert():
    user = get_user()
    return user.expert if user else False

def is_normal():
    user = get_user()
    return not (user.admin or user.expert) if user else False

def is_not_normal():
    return not is_normal()

def get_user_folder(subfolder = None):
    base_folder = os.path.join(app.config['USERS_FOLDER'], '{}'.format(get_uid()))
    if subfolder:
        return os.path.join(base_folder, subfolder)
    else:
        return base_folder

def link_file_to_user(path, name):
    dest = os.path.join(get_user_folder("files"), name)
    os.symlink(path, dest)
    return dest

def library_delete(type, id, user_id = None):
    user_id = get_uid() if not user_id else user_id

    if type == "library_corpora":
        corpus = Corpus.query.filter_by(id = id).first()

        for file_entry in corpus.corpus_files:
            os.remove(file_entry.file.path)
            db.session.delete(file_entry.file)

        db.session.delete(corpus)
        db.session.commit()
    else:
        library = LibraryEngine.query.filter_by(engine_id = id, user_id = user_id).first()
        shutil.rmtree(os.path.realpath(os.path.join(app.config['PRELOADED_ENGINES_FOLDER'], library.engine.path)))
        
        db.session.delete(library.engine)
        db.session.delete(library)
        db.session.commit()

    return True