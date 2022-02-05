"""Create base schema

Revision ID: f30f918b6604
Revises: 
Create Date: 2022-02-03 12:53:08.332490

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f30f918b6604'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'shill_data_sources',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True, primary_key=True),
        sa.Column('chat_id', sa.Integer(), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('ignore', sa.Boolean(), nullable=False, default=False),
        sa.Column('data_source_type', sa.String(), nullable=False, index=True),
    )

def downgrade():
    pass
