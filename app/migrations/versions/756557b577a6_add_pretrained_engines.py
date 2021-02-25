"""Add pretrained engines

Revision ID: 756557b577a6
Revises: 3b9ad36f5408
Create Date: 2020-03-02 10:34:47.574928

"""
from alembic import op
import sqlalchemy as sa

from app import app, db
from app.models import Engine

import os
import sys
import datetime
import yaml
import re
from app.utils import training_log

# revision identifiers, used by Alembic.
revision = '756557b577a6'
down_revision = None
branch_labels = None
depends_on = None

preloaded_path = os.path.join(app.config['BASEDIR'], "preloaded/")


def upgrade():
    for engine_path in [x.path for x in os.scandir(preloaded_path) if x.is_dir()]:
        print(engine_path)
        engine_data = []

        config_file_path = os.path.join(engine_path, 'config.yaml')
        log_file_path = os.path.join(engine_path, 'model/train.log')

        try:
            with open(config_file_path, 'r') as config_file:
                config = yaml.load(config_file, Loader=yaml.FullLoader)
                engine_data = [config["name"], engine_path, config["data"]["src"], config["data"]["trg"]]
        except FileNotFoundError:
            print("No config file found for {}".format(engine_path), file=sys.stderr)
            continue

        try:
            first_date = None
            last_date = None
            with open(log_file_path, 'r') as log_file:
                for line in log_file:
                    groups = re.search(training_log.training_regex, line.strip(), flags=training_log.re_flags)
                    if groups:
                        date_string = "{} {}".format(groups[1], groups[2])
                        date = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

                        if first_date is None:
                            first_date = date
                        else:
                            last_date = date

            engine_data.append(first_date)
            engine_data.append(last_date)
        except FileNotFoundError:
            print("No log file found for {}".format(engine_path), file=sys.stderr)
            continue

        if len(engine_data) == 6:
            eng = Engine(name=engine_data[0], path=engine_data[1], source_id=engine_data[2], target_id=engine_data[3], public=True,
                         launched=engine_data[4],
                         finished=engine_data[5],
                         status='finished')
            db.session.add(eng)
        else:
            print("Could not create engine for {} - incomplete information".format(engine_path))

        db.session.commit()

def downgrade():
    for engine_path in [x for x in os.scandir(preloaded_path) if x.is_dir()]:
        eng = Engine(path=engine_path).query.first()
        if eng:
            db.session.delete(eng)
    db.session.commit()
