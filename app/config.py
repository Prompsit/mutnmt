import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    MUTNMT_FOLDER = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
    PRELOADED_ENGINES_FOLDER = os.path.join(basedir, "preloaded")
    JOEYNMT_FOLDER = os.path.join(basedir, "joeynmt")
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    STORAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "storage")
    FILES_FOLDER = os.path.join(STORAGE_FOLDER, "files")
    ENGINES_FOLDER = os.path.join(STORAGE_FOLDER, "engines")
    USERS_FOLDER = os.path.join(UPLOAD_FOLDER, "users")
    BASE_CONFIG_FOLDER = os.path.join(basedir, "base")

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
