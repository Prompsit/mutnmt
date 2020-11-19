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
import datetime

# revision identifiers, used by Alembic.
revision = '756557b577a6'
down_revision = None
branch_labels = None
depends_on = None

engines = [
    ["Transformer en-es", os.path.join(app.config['BASEDIR'], "preloaded/transformer-new"), "en", "es", '2020-03-04 13:19:44,096', '2020-03-05 04:05:19,946'],
    ["Transformer es-en", os.path.join(app.config['BASEDIR'], "preloaded/transformer-es-en-2"), "es", "en", '2020-03-04 13:19:44,096', '2020-03-05 04:05:19,946']
]

def upgrade():
    for engine in engines:
        eng = Engine(name=engine[0], path=engine[1], source_id=engine[2], target_id=engine[3], public=True,
                        launched=datetime.datetime.strptime(engine[4], '%Y-%m-%d %H:%M:%S,%f'),
                        finished=datetime.datetime.strptime(engine[5], '%Y-%m-%d %H:%M:%S,%f'),
                        status='finished')
        db.session.add(eng)

    db.session.commit()

def downgrade():
    for engine in engines:
        eng = Engine(path=engine[1]).query.first()
        db.session.delete(eng)
    db.session.commit()
