import os
import shutil

from app import app, db, login_manager
from app.models import OAuth, User
from app.utils import user_utils, utils, lang_utils
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
    flash(_('You logged out successfully'), 'success')
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
    import sys
    print(account_info_json, file=sys.stderr)
    username  = account_info_json['name']
    social_id = account_info_json['id']
    email     = account_info_json['email']
    lang      = lang_utils.get_locale()    
    query = User.query.filter_by(social_id=social_id, username = username, email = email)

    try:
      user = query.one()
    except NoResultFound:
      if not app.config['ENABLE_NEW_LOGINS']:
        flash(_('New user logging is temporary disabled'), "warning")
        return False
      user = User(social_id = social_id, username = username, email = email, avatar_url = account_info_json['picture'])
      db.session.add(user)
      db.session.commit()

      print("New user created")

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
    flash(_('You have been logged in successfully'), "success")

  else:
    print("No account info available")
