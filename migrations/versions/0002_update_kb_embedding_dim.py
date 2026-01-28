"""update kb_chunks embedding dimension to 384

Revision ID: 0002_update_kb_embedding_dim
Revises: 2f23ee79cb28
Create Date: 2026-01-28
"""

from alembic import op

revision = "0002_update_kb_embedding_dim"
down_revision = "2f23ee79cb28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(384)")


def downgrade() -> None:
    op.execute("ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(1536)")
