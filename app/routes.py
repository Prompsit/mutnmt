from flask import render_template, url_for, redirect
from flask_login import current_user
from app import app, login_manager, flash, db
from app.utils import utils, user_utils, lang_utils
from .models import User

app.jinja_env.globals.update(**{
    "get_locale": lang_utils.get_locale,
    "user_login_enabled": user_utils.isUserLoginEnabled(),
    "get_user": user_utils.get_user,
    "is_admin": user_utils.is_admin,
    "is_expert": user_utils.is_expert,
    "is_normal": user_utils.is_normal,
    "get_uid": user_utils.get_uid,
    "int": int,
    "Flash": flash.Flash,
    "len": len
})

@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        if user_utils.is_normal():
            return redirect(url_for('library.library_corpora'))
        return redirect(url_for('data.data_index'))
    else:
        return render_template('index.html.jinja2')

@login_manager.user_loader
@utils.condec(login_manager.user_loader, user_utils.isUserLoginEnabled())
def load_user(user_id):
    return User.query.get(int(user_id))