from flask_login import current_user
from app import app

def get_uid():
  if isUserLoginEnabled() and current_user.is_authenticated:
    return current_user.id
  return None

def get_user():
  if isUserLoginEnabled() and current_user.get_id() != None:
    return current_user
  else:
    return None

def isUserLoginEnabled():
  return app.config["USER_LOGIN_ENABLED"] if "USER_LOGIN_ENABLED" in app.config else False