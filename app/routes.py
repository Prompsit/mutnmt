from flask import render_template, url_for, redirect
from flask_login import current_user
from app import app, login_manager, flash, db
from app.utils import utils, user_utils, lang_utils
from app.config import Config
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
    "len": len,
    "infix": app.config['INFIX'],
    "ADMIN_EMAIL": app.config['ADMIN_EMAIL']
})

@app.route('/')
@app.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('library.library_corpora'))
    else:
        return render_template('index.html.jinja2')

@app.route('/about')
def about():
    return render_template('about.html.jinja2', videos=[
        {'name': 'Basics and limitations', 'id': 'eWHvHfIgNDg'},
        {'name': 'Home and users', 'id': 'E_z9OKfyzrk'},
        {'name': 'Data section', 'id': 'qT9TH7zsUkM'},
        {'name': 'Engines section', 'id': 'eOnHYP5VcCI'},
        {'name': 'Training section', 'id': 'kCdZ-s75vP0'},
        {'name': 'Translate section', 'id': '8UqdO-DUvFM'},
        {'name': 'Inspect section', 'id': 'EhQIYPQ-zkQ'},
        {'name': 'Evaluate section', 'id': '93alDhy8IfA'},
        {'name': 'Admin section', 'id': 'vqc4Gx8b2bo'}
    ])

@login_manager.user_loader
@utils.condec(login_manager.user_loader, user_utils.isUserLoginEnabled())
def load_user(user_id):
    return User.query.get(int(user_id))