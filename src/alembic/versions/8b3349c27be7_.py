"""empty message

Revision ID: 8b3349c27be7
Revises: 38d7b3f323bf
Create Date: 2022-02-19 18:24:02.754920

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b3349c27be7"
down_revision = "38d7b3f323bf"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "chat_rooms",
        sa.Column("scrape_count", sa.Integer(), nullable=False, server_default="20"),
    )
    # op.drop_column("chat_rooms", "logo")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "chat_rooms",
        sa.Column("logo", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.drop_column("chat_rooms", "scrape_count")
    # ### end Alembic commands ###
