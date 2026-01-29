"""add tsvector column for kb chunk keyword search

Revision ID: 8a2c1f4c5c2b
Revises: 425f03e85541
Create Date: 2026-01-29
"""

from alembic import op

revision = "8a2c1f4c5c2b"
down_revision = "425f03e85541"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE kb_chunks "
        "ADD COLUMN IF NOT EXISTS content_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )
    op.execute("CREATE INDEX IF NOT EXISTS kb_chunks_content_tsv_idx ON kb_chunks USING GIN (content_tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS kb_chunks_content_tsv_idx")
    op.execute("ALTER TABLE kb_chunks DROP COLUMN IF EXISTS content_tsv")
