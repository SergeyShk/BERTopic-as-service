"""add model creation time

Revision ID: 4d6b1048aef5
Revises: de6b38f9aed7
Create Date: 2022-01-29 22:51:04.447698

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '4d6b1048aef5'
down_revision = 'de6b38f9aed7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('topic_model', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('topic_model', 'created_at')
    # ### end Alembic commands ###