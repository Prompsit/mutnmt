from flask import render_template
from app import app, login_manager
from app.utils import utils, user_utils, lang_utils
from .models import User

app.jinja_env.globals.update(**{
  "get_locale": lang_utils.get_locale,
  "user_login_enabled": user_utils.isUserLoginEnabled()
})

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html.jinja2')

@login_manager.user_loader
@utils.condec(login_manager.user_loader, user_utils.isUserLoginEnabled())
def load_user(user_id):
  return User.query.get(int(user_id))