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

# revision identifiers, used by Alembic.
revision = '756557b577a6'
down_revision = '3b9ad36f5408'
branch_labels = None
depends_on = None

engines = [
    ["Transformer en-es", os.path.join(app.config['BASEDIR'], "preloaded/transformer-new"), "en", "es"],
    ["Transformer es-en", os.path.join(app.config['BASEDIR'], "preloaded/transformer-es-en-2"), "es", "en"]
]

def upgrade():
    for engine in engines:
        eng = Engine(name=engine[0], path=engine[1], source_id=engine[2], target_id=engine[3], public=True)
        db.session.add(eng)

    db.session.commit()

def downgrade():
    for engine in engines:
        eng = Engine(path=engine[1]).query.first()
        db.session.delete(eng)
    db.session.commit()
