from app import db

from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from sqlalchemy.ext.associationproxy import association_proxy

import datetime

class Language(db.Model):
    __tablename__ = 'language'
    code = db.Column(db.String(3), primary_key=True)
    name = db.Column(db.String(64))

class File(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    path = db.Column(db.String(250), unique=True)
    hash = db.Column(db.String(250))
    uploaded = db.Column(db.Date, default=datetime.datetime.utcnow)
    lines = db.Column(db.Integer)
    words = db.Column(db.Integer)
    chars = db.Column(db.Integer)
    public = db.Column(db.Boolean, default=False)

    language_id = db.Column(db.String(3), db.ForeignKey('language.code'))
    language = db.relationship("Language", backref="files")

    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploader = db.relationship("User", backref="files")

class Corpus(db.Model):
    __tablename__ = 'corpus'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    type = db.Column(db.String(64))

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship("User", backref="corpora")

    files = association_proxy("corpus_files", "files")
    languages = association_proxy("corpus_languages", "languages")

class Corpus_File(db.Model):
    __tablename__ = 'corpus_file'
    id = db.Column(db.Integer, primary_key=True)
    corpus_id = db.Column(db.Integer, db.ForeignKey('corpus.id'))
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    role = db.Column(db.String(64))

    corpus = db.relationship(Corpus, backref = db.backref("corpus_files", cascade="all, delete-orphan"))
    file = db.relationship("File")

    __table_args__ = (
        db.UniqueConstraint('corpus_id', 'file_id'),
    )

    def __init__(self, file = None, corpus = None, role = None):
        self.file = file
        self.corpus = corpus
        self.role = role

class Corpus_Language(db.Model):
    __tablename__ = 'corpus_language'
    id = db.Column(db.Integer, primary_key=True)
    corpus_id = db.Column(db.Integer, db.ForeignKey('corpus.id'))
    language_id = db.Column(db.Integer, db.ForeignKey('language.code'))
    role = db.Column(db.String(64))

    corpus = db.relationship(Corpus, backref = db.backref("corpus_languages", cascade="all, delete-orphan"))
    language = db.relationship("Language")

    __table_args__ = (
        db.UniqueConstraint('corpus_id', 'language_id'),
    )

    def __init__(self, language_id = None, corpus = None, role = None):
        self.language_id = language_id
        self.corpus = corpus
        self.role = role

class Engine(db.Model):
    __tablename__ = 'engine'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    path = db.Column(db.String(1024))
    public = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(64))

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship("User", backref="engines")

class Corpus_Engine(db.Model):
    __tablename__ = 'corpus_engine'
    id = db.Column(db.Integer, primary_key=True)
    corpus_id = db.Column(db.Integer, db.ForeignKey('corpus.id'))
    engine_id = db.Column(db.Integer, db.ForeignKey('engine.id'))
    phase = db.Column(db.String(64))

    __table_args__ = (
        db.UniqueConstraint('corpus_id', 'engine_id', 'phase'),
    )

class User(UserMixin, db.Model):
    __tablename__   = 'user'
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(250))
    social_id       = db.Column(db.String(250))
    email           = db.Column(db.String(60), unique=True)
    admin           = db.Column(db.Boolean, default=False)
    banned          = db.Column(db.Boolean, default=False)
    lang            = db.Column(db.String(32))
    avatar_url      = db.Column(db.String(250))

class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = "flask_dance_oauth"
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user    = db.relationship("User")