import os
import re
import shutil
import sys
import datetime

import yaml

from app import app, db, login_manager
from app.models import OAuth, User, UserLanguage, LibraryEngine, Engine
from app.utils import user_utils, utils, lang_utils, training_log
from flask_login import login_required, current_user, login_user, logout_user

from flask import Blueprint, render_template, abort, flash, redirect, url_for, jsonify
from flask_dance.consumer import oauth_authorized
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.contrib.google import make_google_blueprint, google
from flask_babel import _
from sqlalchemy.orm.exc import NoResultFound

auth_blueprint = Blueprint('auth', __name__, template_folder='templates')

if app.config['OAUTHLIB_INSECURE_TRANSPORT']:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

login_manager.login_view = 'google.login'
login_manager.login_message = ''

@auth_blueprint.route('/logout')
@utils.condec(login_required, user_utils.isUserLoginEnabled())
def logout():
    logout_user()
    return redirect(url_for('index'))

google_blueprint = make_google_blueprint(
    scope = ["openid",
             "https://www.googleapis.com/auth/userinfo.email",
             "https://www.googleapis.com/auth/userinfo.profile"])

if user_utils.isUserLoginEnabled():
    app.register_blueprint(google_blueprint, url_prefix = '/auth')
    google_blueprint.storage = SQLAlchemyStorage(OAuth, db.session, user = current_user)

@oauth_authorized.connect_via(google_blueprint)
def google_logged_in(blueprint, token):
    account_info = blueprint.session.get(app.config['GOOGLE_USER_DATA_URL'])

    if account_info.ok:
        account_info_json = account_info.json()
        username  = account_info_json['name']
        social_id = account_info_json['id']
        email     = account_info_json['email']
        lang      = lang_utils.get_locale()
        query = User.query.filter_by(social_id=social_id, username = username, email = email)

        try:
            user = query.one()
        except NoResultFound:
            if not app.config['ENABLE_NEW_LOGINS']:
                if app.config['WHITELIST'] is None or email not in app.config['WHITELIST']:
                    flash(_('New user logging is temporary disabled'), "warning")
                    return False
            user = User(social_id = social_id, username = username, email = email, avatar_url = account_info_json['picture'])
            db.session.add(user)
            db.session.commit()

            print("New user created")

            # Create user filesystem
            user_path = os.path.join(app.config['USERS_FOLDER'], "{}".format(user.id))
            os.mkdir(user_path)

            engines_path = os.path.join(user_path, "engines")
            os.mkdir(engines_path)

            # Add languages to user
            with open(os.path.join(app.config['MUTNMT_FOLDER'], 'scripts/langs.txt')) as langs_file:
                for line in langs_file:
                    line = line.strip()
                    if line:
                        data = line.split(',')
                        user_language = UserLanguage(code=data[0], name=data[1], user_id=user.id)
                        db.session.add(user_language)
                db.session.commit()

            # Add pretrained engines to user
            add_pretrained_engines(user.id)

        # Update admins
        for i in app.config['ADMINS']:
            try:
                adminuser = User.query.filter(User.email == i).one()
                adminuser.admin = True
            except NoResultFound:
                pass

        db.session.commit()

        # Check bans
        if user.email in app.config['BANNED_USERS'] or user.banned:
            flash(_('User temporary banned'), "danger")
            return False

        login_user(user)

    else:
        print("No account info available")

@auth_blueprint.route('/demo')
def demo_log_in():
    # We log out the user if the session is active
    if current_user:
        logout_user()

    # If demo user is not present, add
    if User.query.filter_by(demo=True).first() is None:
        demo_user = User(id=-1, username='Amun', social_id='DEMO', email='demo@example.com', demo=True,
                         avatar_url='/img/amun.png')
        db.session.add(demo_user)
        db.session.commit()

        # Add languages to user
        with open(os.path.join(app.config['MUTNMT_FOLDER'], 'scripts/langs.txt')) as langs_file:
            for line in langs_file:
                line = line.strip()
                if line:
                    data = line.split(',')
                    user_language = UserLanguage(code=data[0], name=data[1], user_id=demo_user.id)
                    db.session.add(user_language)
            db.session.commit()

    demo_user = User.query.filter_by(demo=True).first()

    if demo_user:
        login_user(demo_user)
        return redirect(url_for('library.library_corpora'))
    else:
        return redirect(url_for('index'))


def add_pretrained_engines(user_id):
    preloaded_path = os.path.join(app.config['BASEDIR'], "preloaded/")

    for engine_path in [x.path for x in os.scandir(preloaded_path) if x.is_dir()]:
        print("Adding {}".format(engine_path))
        engine_data = []

        config_file_path = os.path.join(engine_path, 'config.yaml')
        log_file_path = os.path.join(engine_path, 'model/train.log')

        try:
            with open(config_file_path, 'r') as config_file:
                config = yaml.load(config_file, Loader=yaml.FullLoader)
                engine_data = [config["name"], engine_path, config["data"]["src"], config["data"]["trg"]]
        except FileNotFoundError:
            print("No config file found for {}".format(engine_path), file=sys.stderr)
            continue

        try:
            first_date = None
            last_date = None
            with open(log_file_path, 'r') as log_file:
                for line in log_file:
                    groups = re.search(training_log.training_regex, line.strip(), flags=training_log.re_flags)
                    if groups:
                        date_string = "{} {}".format(groups[1], groups[2])
                        date = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

                        if first_date is None:
                            first_date = date
                        else:
                            last_date = date

            engine_data.append(first_date)
            engine_data.append(last_date)
        except FileNotFoundError:
            print("No log file found for {}".format(engine_path), file=sys.stderr)
            continue

        if len(engine_data) == 6:
            source_lang = UserLanguage.query.filter_by(code=engine_data[2], user_id=user_id).one()
            target_lang = UserLanguage.query.filter_by(code=engine_data[3], user_id=user_id).one()
            eng = Engine(name=engine_data[0], path=engine_data[1], user_source_id=source_lang.id, user_target_id=target_lang.id,
                         public=False,
                         launched=engine_data[4],
                         finished=engine_data[5],
                         status='finished')
            db.session.add(eng)
            db.session.commit()

            u = User.query.filter_by(id=user_id).one()
            library_engine = LibraryEngine(eng, u)
            db.session.add(library_engine)
            db.session.commit()
        else:
            print("Could not create engine for {} - incomplete information".format(engine_path))

        db.session.commit()
