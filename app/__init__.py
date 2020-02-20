from flask import Flask, render_template

app = Flask(__name__, static_folder='static', static_url_path='')

from .blueprints.data.views import data_blueprint
from .blueprints.library.views import library_blueprint
from .blueprints.train.views import train_blueprint

blueprints = [["/data", data_blueprint],
                ["/library", library_blueprint],
                ["/train", train_blueprint]]

for blueprint in blueprints:
  app.register_blueprint(blueprint[1], url_prefix=blueprint[0])

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html.jinja2')