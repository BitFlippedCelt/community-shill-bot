"""Create link tracking table

Revision ID: c8e3066ad94f
Revises: f30f918b6604
Create Date: 2022-02-03 18:22:04.212668

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8e3066ad94f'
down_revision = 'f30f918b6604'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'shill_link_tracker',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True, primary_key=True),
        sa.Column('chat_id', sa.Integer(), nullable=False, index=True),
        sa.Column('link', sa.String(), nullable=False),
        sa.Column('link_type', sa.String(), nullable=False),
        sa.Column('checked', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now())
    )


def downgrade():
    pass
