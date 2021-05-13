"""User notes

Revision ID: c0c7a3a22cd8
Revises: 54d22e46348c
Create Date: 2021-05-04 12:12:18.381609

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0c7a3a22cd8'
down_revision = '1b6f00354bc0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('notes', sa.String(length=280), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'notes')
    # ### end Alembic commands ###