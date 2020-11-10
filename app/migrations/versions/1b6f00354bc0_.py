"""Insert topics

Revision ID: 1b6f00354bc0
Revises: dd1bcfc4cb0a
Create Date: 2020-10-22 08:45:32.372494

"""
from alembic import op
import sqlalchemy as sa

from app import app, db
from app.models import Topic


# revision identifiers, used by Alembic.
revision = '1b6f00354bc0'
down_revision = 'dd1bcfc4cb0a'
branch_labels = None
depends_on = None

TOPICS = ["Administrative", "Legal", "Technical"]


def upgrade():
    for topic in TOPICS:
        topic_obj = Topic(name=topic)
        db.session.add(topic_obj)
    db.session.commit()


def downgrade():
    for topic in TOPICS:
        topic_obj = Topic.query.filter_by(name=topic).first()
        db.session.delete(topic_obj)
    db.session.commit()
