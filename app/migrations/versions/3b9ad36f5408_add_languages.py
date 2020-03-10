"""Add languages

Revision ID: 3b9ad36f5408
Revises: 
Create Date: 2020-03-02 10:30:56.658847

"""
from alembic import op
import sqlalchemy as sa

from app import app, db
from app.models import Language

# revision identifiers, used by Alembic.
revision = '3b9ad36f5408'
down_revision = None
branch_labels = None
depends_on = None

languages = [
    ["en", "English"], ["es", "Spanish"],
    ["de", "German"], ["ca", "Catalan"]
]

def upgrade():
    for language in languages:
        lang = Language(code = language[0], name = language[1])
        db.session.add(lang)

    db.session.commit()


def downgrade():
    for language in languages:
        lang = Language.query.filter_by(code = language[0]).first()
        db.session.remove(lang)
    db.session.commit()

