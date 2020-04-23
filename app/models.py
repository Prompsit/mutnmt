from app import db

from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from sqlalchemy.ext.associationproxy import association_proxy

import datetime

class Language(db.Model):
    __tablename__ = 'language'
    code = db.Column(db.String(3), primary_key=True)
    name = db.Column(db.String(64))

class Resource(db.Model):
    __tablename__ = 'resource'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    path = db.Column(db.String(250), unique=True)
    hash = db.Column(db.String(250))
    uploaded = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    public = db.Column(db.Boolean, default=False)

    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploader = db.relationship("User", backref="resources")

class File(Resource):
    __tablename__ = 'file'
    id = db.Column(db.Integer, db.ForeignKey('resource.id'), primary_key=True)

    lines = db.Column(db.Integer)
    words = db.Column(db.Integer)
    chars = db.Column(db.Integer)

    language_id = db.Column(db.String(3), db.ForeignKey('language.code'))
    language = db.relationship("Language", backref="files")


class Engine(Resource):
    __tablename__ = 'engine'
    id = db.Column(db.Integer, db.ForeignKey('resource.id'), primary_key=True)
    
    status = db.Column(db.String(64))
    launched = db.Column(db.DateTime)
    finished = db.Column(db.DateTime)

    source_id = db.Column(db.String(3), db.ForeignKey('language.code'))
    source = db.relationship("Language", backref = db.backref("engines_source", cascade="all, delete-orphan"), foreign_keys=[source_id])

    target_id = db.Column(db.String(3), db.ForeignKey('language.code'))
    target = db.relationship("Language", backref = db.backref("engines_target", cascade="all, delete-orphan"), foreign_keys=[target_id])

    def __repr__(self):
        return "Engine {}, {}, {}, {}".format(self.name, self.status, self.source_id, self.target_id)

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.id == other.id
        )

class Corpus(db.Model):
    __tablename__ = 'corpus'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    type = db.Column(db.String(64))
    public = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship("User", backref="corpora")

    files = association_proxy("corpus_files", "files")

    source_id = db.Column(db.String(3), db.ForeignKey('language.code'))
    source = db.relationship("Language", backref = db.backref("corpus_source", cascade="all, delete-orphan"), foreign_keys=[source_id])

    target_id = db.Column(db.String(3), db.ForeignKey('language.code'))
    target = db.relationship("Language", backref = db.backref("corpus_target", cascade="all, delete-orphan"), foreign_keys=[target_id])

class Corpus_File(db.Model):
    __tablename__ = 'corpus_file'
    id = db.Column(db.Integer, primary_key=True)
    corpus_id = db.Column(db.Integer, db.ForeignKey('corpus.id'))
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    role = db.Column(db.String(64))

    corpus = db.relationship(Corpus, backref = db.backref("corpus_files", cascade="all, delete-orphan"))
    file = db.relationship("File", backref = db.backref("corpora", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint('corpus_id', 'file_id'),
    )

    def __init__(self, file = None, corpus = None, role = None):
        self.file = file
        self.corpus = corpus
        self.role = role

class Corpus_Engine(db.Model):
    __tablename__ = 'corpus_engine'
    id = db.Column(db.Integer, primary_key=True)
    corpus_id = db.Column(db.Integer, db.ForeignKey('corpus.id'))
    engine_id = db.Column(db.Integer, db.ForeignKey('engine.id'))
    phase = db.Column(db.String(64))

    engine = db.relationship(Engine, backref = db.backref("corpora_engines", cascade="all, delete-orphan"))
    corpus = db.relationship("Corpus")

    __table_args__ = (
        db.UniqueConstraint('corpus_id', 'engine_id', 'phase'),
    )

    def __init__(self, corpus = None, engine = None, phase = None):
        self.corpus = corpus
        self.engine = engine
        self.phase = phase

class User(UserMixin, db.Model):
    __tablename__   = 'user'
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(250))
    social_id       = db.Column(db.String(250))
    email           = db.Column(db.String(60), unique=True)
    admin           = db.Column(db.Boolean, default=False)
    expert          = db.Column(db.Boolean, default=False)
    banned          = db.Column(db.Boolean, default=False)
    lang            = db.Column(db.String(32))
    avatar_url      = db.Column(db.String(250))

    corpora = association_proxy("user_corpora", "corpora")
    engines = association_proxy("user_engines", "engines")
    running_engines = association_proxy("user_running_engines", "running_engines")

class LibraryCorpora(db.Model):
    __tablename__ = 'library_corpora'
    id = db.Column(db.Integer, primary_key=True)

    corpus_id = db.Column(db.Integer, db.ForeignKey('corpus.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship(User, backref = db.backref("user_corpora", cascade="all, delete-orphan"))
    corpus = db.relationship("Corpus", backref = db.backref("libraries", cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'corpus_id'),
    )

    def __init__(self, file=None, user=None):
        self.user = user
        self.corpus = corpus

class LibraryEngine(db.Model):
    __tablename__ = 'library_engines'
    id = db.Column(db.Integer, primary_key=True)

    engine_id = db.Column(db.Integer, db.ForeignKey('engine.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship(User, backref = db.backref("user_engines", cascade="all, delete-orphan"))
    engine = db.relationship("Engine")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'engine_id'),
    )

    def __init__(self, engine=None, user=None):
        self.user = user
        self.engine = engine

class RunningEngines(db.Model):
    __tablename__ = 'running_engines'
    id = db.Column(db.Integer, primary_key=True)

    engine_id = db.Column(db.Integer, db.ForeignKey('engine.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship(User, backref = db.backref("user_running_engines", cascade="all, delete-orphan"))
    engine = db.relationship("Engine")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'engine_id'),
    )

    def __init__(self, engine=None, user=None):
        self.user = user
        self.engine = engine


class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = "flask_dance_oauth"
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user    = db.relationship("User")