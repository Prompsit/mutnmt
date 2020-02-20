from app import db

from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage

class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(250), unique=True)
    hash = db.Column(db.String(250))
    owner = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return '<{}, {}, {}, {}>'.format(self.id, self.path, self.owner, self.hash)

class BilingualCorpus(db.Model):
    __tablename__ = 'bilingual_corpora'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    owner = db.Column(db.Integer, db.ForeignKey('users.id'))
    source = db.Column(db.Integer, db.ForeignKey('files.id'))
    target = db.Column(db.Integer, db.ForeignKey('files.id'))

    __table_args__ = (
        db.UniqueConstraint('source', 'target'),
    )

    def __repr__(self):
        return '<{}, {}, {}, {}, {}>'.format(id, name, owner, source, target)

class User(UserMixin, db.Model):
    __tablename__   = 'users'
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(250))
    social_id       = db.Column(db.String(250))
    email           = db.Column(db.String(60), unique=True)
    admin           = db.Column(db.Boolean, default=False)
    banned          = db.Column(db.Boolean, default=False)
    lang            = db.Column(db.String(32))
    avatar_url      = db.Column(db.String(250))

    file = db.relationship("File", backref="User")
    bilingualcorpus = db.relationship("BilingualCorpus", backref="User")

class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = "flask_dance_oauth"
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user    = db.relationship("User")