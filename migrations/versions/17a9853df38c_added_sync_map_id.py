"""added sync map id

Revision ID: 17a9853df38c
Revises: ba4d9c065ff7
Create Date: 2018-03-24 19:05:47.040911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17a9853df38c'
down_revision = 'ba4d9c065ff7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('sync_map_sid', sa.String(length=64), nullable=True))
    op.drop_column('users', 'sync_map_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('sync_map_id', sa.VARCHAR(length=64), autoincrement=False, nullable=True))
    op.drop_column('users', 'sync_map_sid')
    # ### end Alembic commands ###
