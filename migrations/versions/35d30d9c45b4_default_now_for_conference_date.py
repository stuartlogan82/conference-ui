"""default now for conference date

Revision ID: 35d30d9c45b4
Revises: 17a9853df38c
Create Date: 2018-03-27 14:11:54.786298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35d30d9c45b4'
down_revision = '17a9853df38c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_conferences_date_created'), 'conferences', ['date_created'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_conferences_date_created'), table_name='conferences')
    # ### end Alembic commands ###
