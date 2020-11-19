import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    BASEDIR = basedir
    MUTNMT_FOLDER = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
    TMP_FOLDER = '/tmp'
    LIST_FOLDER = os.path.join(basedir, 'list')
    PRELOADED_ENGINES_FOLDER = os.path.join(basedir, "preloaded")
    JOEYNMT_FOLDER = os.path.join(basedir, "joeynmt")
    DATA_FOLDER = os.path.join(MUTNMT_FOLDER, "data")
    USERSPACE_FOLDER = os.path.join(DATA_FOLDER, "userspace")
    STORAGE_FOLDER = os.path.join(USERSPACE_FOLDER, "storage")
    FILES_FOLDER = os.path.join(STORAGE_FOLDER, "files")
    ENGINES_FOLDER = os.path.join(STORAGE_FOLDER, "engines")
    USERS_FOLDER = os.path.join(USERSPACE_FOLDER, "users")
    BASE_CONFIG_FOLDER = os.path.join(basedir, "base")
    EVALUATORS_FOLDER = os.path.join(BASEDIR, "blueprints/evaluate/evaluators")

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(DATA_FOLDER, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = 'development key' # change by your own
    DEBUG      = False

    # Uncomment it to enable translations. Follow instructions in README.md to add more languages
    LANGUAGES = { 'ca': 'Català', 'en': 'English', 'es': 'Spanish' }

    USER_LOGIN_ENABLED          = True
    ENABLE_NEW_LOGINS           = True
    BANNED_USERS                = []
    OAUTHLIB_INSECURE_TRANSPORT = True # True also behind firewall,  False -> require HTTPS
    GOOGLE_OAUTH_CLIENT_ID      = '481103200747-c9g4nsv7ud7ojj9dgv5s1nvhsdkvqji3.apps.googleusercontent.com'
    GOOGLE_OAUTH_CLIENT_SECRET  = '__TyuCk8eD0kR594K18MitZw'
    GOOGLE_USER_DATA_URL        = '/oauth2/v1/userinfo'

    with open(os.path.join(LIST_FOLDER, 'admin.list'), 'r') as admin_file:
        ADMINS = [line.strip() for line in admin_file if line.strip() != ""]

    # Celery
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERYD_CONCURRENCY = 4
