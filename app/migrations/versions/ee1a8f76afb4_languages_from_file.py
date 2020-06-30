"""Languages from file

Revision ID: ee1a8f76afb4
Revises: 4c731534bbcf
Create Date: 2020-06-30 08:13:02.810567

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app import app, db
from app.models import Language
import os

# revision identifiers, used by Alembic.
revision = 'ee1a8f76afb4'
down_revision = '4c731534bbcf'
branch_labels = None
depends_on = None

languages = []
with open(os.path.join(app.config['MUTNMT_FOLDER'], 'scripts/langs.txt'), 'r') as langs_file:
    for line in langs_file:
        line = line.strip()
        lang_data = line.split(',')
        languages.append([lang_data[0], lang_data[1]])

def upgrade():
    Language.query.delete()
    
    for language in languages:
        lang = Language(code = language[0], name = language[1])
        db.session.add(lang)

    db.session.commit()


def downgrade():
    for language in languages:
        lang = Language.query.filter_by(code = language[0]).first()
        if lang:
            db.session.delete(lang)
    db.session.commit()
