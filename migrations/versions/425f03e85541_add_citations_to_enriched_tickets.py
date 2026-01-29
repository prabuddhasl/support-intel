"""add citations to enriched_tickets

Revision ID: 425f03e85541
Revises: 0002_update_kb_embedding_dim
Create Date: 2026-01-28 15:39:58.112294

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



revision = '425f03e85541'
down_revision = '0002_update_kb_embedding_dim'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enriched_tickets",
        sa.Column("citations", postgresql.JSONB(astext_type=postgresql.TEXT()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("enriched_tickets", "citations")
