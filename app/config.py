import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = 'development key' # change by your own
    DEBUG      = False

    # Uncomment it to enable translations. Follow instructions in README.md to add more languages
    LANGUAGES = { 'ca': 'Català', 'en': 'English', 'es': 'Spanish' }

    USER_LOGIN_ENABLED          = True
    ENABLE_NEW_LOGINS           = True
    ADMINS                      = ['sjarmero@gmail.com']
    BANNED_USERS                = []
    OAUTHLIB_INSECURE_TRANSPORT = True # True also behind firewall,  False -> require HTTPS
    GOOGLE_OAUTH_CLIENT_ID      = '481103200747-c9g4nsv7ud7ojj9dgv5s1nvhsdkvqji3.apps.googleusercontent.com'
    GOOGLE_OAUTH_CLIENT_SECRET  = '__TyuCk8eD0kR594K18MitZw'
    GOOGLE_USER_DATA_URL        = '/oauth2/v1/userinfo'
