from .config import Config

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel
from flask_dropzone import Dropzone
from flask_migrate import upgrade as _upgrade
from werkzeug.middleware.proxy_fix import ProxyFix

import os

app = Flask(__name__, static_folder='static', static_url_path='')

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
babel = Babel(app)
dropzone = Dropzone(app)
migrate = Migrate(app, db)

if app.config['USE_PROXY_FIX']:
    app.wsgi_app = ProxyFix(app.wsgi_app)

# Blueprints
from .blueprints.auth.views import auth_blueprint
from .blueprints.data.views import data_blueprint
from .blueprints.library.views import library_blueprint
from .blueprints.train.views import train_blueprint
from .blueprints.translate.views import translate_blueprint
from .blueprints.inspect.views import inspect_blueprint
from .blueprints.evaluate.views import evaluate_blueprint
from .blueprints.admin.views import admin_blueprint
from .blueprints.tour.views import tour_blueprint

blueprints = [["/auth", auth_blueprint],
                ["/data", data_blueprint],
                ["/library", library_blueprint],
                ["/train", train_blueprint],
                ["/translate", translate_blueprint],
                ["/inspect", inspect_blueprint],
                ["/evaluate", evaluate_blueprint],
                ["/admin", admin_blueprint],
                ["/tour", tour_blueprint]]

for blueprint in blueprints:
    app.register_blueprint(blueprint[1], url_prefix=blueprint[0])

from app import routes, models

db.create_all()
db.session.commit()

for running_engine in models.RunningEngines.query.all():
    db.session.delete(running_engine)    
    db.session.commit()

TOPICS = ["General", "Technical", "Legal", "Financial", "Medical", "Religion", "Politics", "Administrative",
          "Subtitles", "Patents", "News", "Books", "Other"]

for topic in TOPICS:
    if models.Topic.query.filter_by(name=topic).first() is None:
        topic_obj = models.Topic(name=topic)
        db.session.add(topic_obj)
db.session.commit()

# If demo user is not present, add
if models.User.query.filter_by(demo=True).first() is None:
    demo_user = models.User(id=-1, username='Demo', social_id='DEMO', email='demo@example.com', demo=True)
    db.session.add(demo_user)

folders = ['USERSPACE_FOLDER', 'STORAGE_FOLDER', 'FILES_FOLDER', 'ENGINES_FOLDER', 'USERS_FOLDER']

for folder in folders:
    try:
        os.stat(app.config[folder])
    except:
        os.mkdir(app.config[folder])

from app.utils.GPUManager import GPUManager
GPUManager.scan_devices(reset=True, is_admin=True)
