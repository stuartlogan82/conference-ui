"""initial migration

Revision ID: 5baa5fa8661a
Revises: 
Create Date: 2018-02-23 19:12:28.866452

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5baa5fa8661a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('conferences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('call_sid', sa.String(length=64), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('account_sid', sa.String(length=64), nullable=True),
    sa.Column('date_created', sa.String(length=64), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conferences_call_sid'), 'conferences', ['call_sid'], unique=True)
    op.create_table('participants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=32), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('direction', sa.String(length=16), nullable=True),
    sa.Column('call_sid', sa.String(length=64), nullable=True),
    sa.Column('conference_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['conference_id'], ['conferences.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participants_call_sid'), 'participants', ['call_sid'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_participants_call_sid'), table_name='participants')
    op.drop_table('participants')
    op.drop_index(op.f('ix_conferences_call_sid'), table_name='conferences')
    op.drop_table('conferences')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###
