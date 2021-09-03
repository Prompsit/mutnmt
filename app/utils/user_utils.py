from flask_login import current_user
from app import app, db
from app.models import Corpus, LibraryEngine, LibraryCorpora, Corpus_Engine, User
from sqlalchemy import and_
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

def get_user_folder(subfolder = None, user_id = None):
    base_folder = os.path.join(app.config['USERS_FOLDER'], '{}'.format(get_uid() if user_id is None else user_id))
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
        library = LibraryCorpora.query.filter_by(corpus_id = id, user_id = user_id).first()
        if LibraryCorpora.query.filter_by(corpus_id = id).filter(LibraryCorpora.user_id != user_id).count() == 0:
            for file_entry in library.corpus.corpus_files:
                os.remove(file_entry.file.path)
                db.session.delete(file_entry.file)

            db.session.delete(library.corpus)

        db.session.delete(library)
        db.session.commit()
    else:
        library = LibraryEngine.query.filter_by(engine_id = id, user_id = user_id).first()

        if LibraryEngine.query.filter_by(engine_id = id).filter(LibraryEngine.user_id != user_id).count() == 0:
            shutil.rmtree(library.engine.path)
            db.session.delete(library.engine)

        db.session.delete(library)
        db.session.commit()

    return True

def get_user_corpora(user_id=None, public=False, used=False, not_used=False):
    user_id = user_id if user_id else get_uid()
    if public:
        return LibraryCorpora.query.filter(LibraryCorpora.corpus_id.notin_(
                db.session.query(LibraryCorpora.corpus_id).filter_by(user_id=user_id)
            )).filter(LibraryCorpora.corpus.has(and_(
                Corpus.visible == True,
                Corpus.public == True,
                Corpus.owner_id != user_id,
                Corpus.owner_id == LibraryCorpora.user_id
            ))).order_by(LibraryCorpora.id.desc())
    elif used:
        return LibraryCorpora.query.filter(LibraryCorpora.corpus.has(
            and_(Corpus.corpus_engines,
                 Corpus_Engine.is_info == True,
                 LibraryCorpora.user_id == Corpus.owner_id
            )
        ))
    elif not_used:
        return LibraryCorpora.query.filter(LibraryCorpora.corpus.has(
            and_(
                ~ Corpus.corpus_engines.any(),
                Corpus_Engine.is_info == True,
                LibraryCorpora.user_id == Corpus.owner_id
            )
        ))
    else:
        return LibraryCorpora.query.filter(LibraryCorpora.user_id == user_id) \
                .filter(LibraryCorpora.corpus.has(and_(
                    Corpus.visible == True
                ))).order_by(LibraryCorpora.id.desc())