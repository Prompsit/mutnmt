from flask_login import current_user
from app import app

import os

def get_uid():
    if isUserLoginEnabled() and current_user.is_authenticated:
        return current_user.id
    return None

def get_user():
    if isUserLoginEnabled() and current_user and current_user.get_id() != None:
        return current_user
    else:
        return None

def isUserLoginEnabled():
    return app.config["USER_LOGIN_ENABLED"] if "USER_LOGIN_ENABLED" in app.config else False

def get_user_folder(subfolder = None):
    base_folder = os.path.join(app.config['USERS_FOLDER'], '{}'.format(get_uid()))
    if subfolder:
        return os.path.join(base_folder, subfolder)
    else:
        return base_folder

def link_file_to_user(path, name):
    dest = os.path.join(get_user_folder("files"), name)
    os.symlink(path, dest)
    return dest