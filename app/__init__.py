from .config import Config

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel
from flask_dropzone import Dropzone

import os

app = Flask(__name__, static_folder='static', static_url_path='')

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
babel = Babel(app)
dropzone = Dropzone(app)
migrate = Migrate(app, db)

# Blueprints
from .blueprints.auth.views import auth_blueprint
from .blueprints.data.views import data_blueprint
from .blueprints.library.views import library_blueprint
from .blueprints.train.views import train_blueprint
from .blueprints.translate.views import translate_blueprint
from .blueprints.inspect.views import inspect_blueprint
from .blueprints.evaluate.views import evaluate_blueprint
from .blueprints.admin.views import admin_blueprint

blueprints = [["/auth", auth_blueprint],
                ["/data", data_blueprint],
                ["/library", library_blueprint],
                ["/train", train_blueprint],
                ["/translate", translate_blueprint],
                ["/inspect", inspect_blueprint],
                ["/evaluate", evaluate_blueprint],
                ["/admin", admin_blueprint]]

for blueprint in blueprints:
    app.register_blueprint(blueprint[1], url_prefix=blueprint[0])

from app import routes, models

db.create_all()
db.session.commit()

try:
    os.stat(app.config['UPLOAD_FOLDER'])
except:
    os.mkdir(app.config['UPLOAD_FOLDER'])

try:
    os.stat(app.config['STORAGE_FOLDER'])
except:
    os.mkdir(app.config['STORAGE_FOLDER'])

try:
    os.stat(app.config['FILES_FOLDER'])
except:
    os.mkdir(app.config['FILES_FOLDER'])

try:
    os.stat(app.config['ENGINES_FOLDER'])
except:
    os.mkdir(app.config['ENGINES_FOLDER'])

try:
    os.stat(app.config['USERS_FOLDER'])
except:
    os.mkdir(app.config['USERS_FOLDER'])