"""add embeddings to kb_chunks

Revision ID: 2f23ee79cb28
Revises: 0001_init
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "2f23ee79cb28"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("kb_chunks", sa.Column("embedding", Vector(1536)))


def downgrade() -> None:
    op.drop_column("kb_chunks", "embedding")
