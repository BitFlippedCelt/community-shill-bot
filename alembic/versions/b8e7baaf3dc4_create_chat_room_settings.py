"""Create chat room settings

Revision ID: b8e7baaf3dc4
Revises: c8e3066ad94f
Create Date: 2022-02-04 08:12:09.517096

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b8e7baaf3dc4"
down_revision = "c8e3066ad94f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shill_chat_room_settings",
        sa.Column(
            "id", sa.Integer(), nullable=False, autoincrement=True, primary_key=True
        ),
        sa.Column("chat_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("cta_link", sa.String()),
        sa.Column("cta_text", sa.String()),
        sa.Column("dex_link", sa.String()),
        sa.Column("cmc_link", sa.String()),
        sa.Column("cg_link", sa.String()),
        sa.Column("tags", sa.String()),
        sa.Column("logo", sa.BLOB()),
        sa.Column("logo_mime", sa.String()),
        sa.Column("scrape_interval", sa.Integer(), nullable=False, default=60 * 60),
        sa.Column("update_interval", sa.Integer(), nullable=False, default=60 * 30),
    )


def downgrade():
    pass
