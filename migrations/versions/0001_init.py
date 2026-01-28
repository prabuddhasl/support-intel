"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-01-28

"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enriched_tickets",
        sa.Column("ticket_id", sa.Text, primary_key=True),
        sa.Column("last_event_id", sa.Text, nullable=True),
        sa.Column("subject", sa.Text, nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("channel", sa.Text, nullable=True),
        sa.Column("priority", sa.Text, nullable=True),
        sa.Column("customer_id", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("category", sa.Text, nullable=True),
        sa.Column("sentiment", sa.Text, nullable=True),
        sa.Column("risk", sa.Float, nullable=True),
        sa.Column("suggested_reply", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.Text, primary_key=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "kb_documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("content_type", sa.Text, nullable=True),
        sa.Column("sha256", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "doc_id",
            sa.Integer,
            sa.ForeignKey("kb_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("heading_path", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
    )

    op.create_index("kb_chunks_doc_id_idx", "kb_chunks", ["doc_id"])


def downgrade() -> None:
    op.drop_index("kb_chunks_doc_id_idx", table_name="kb_chunks")
    op.drop_table("kb_chunks")
    op.drop_table("kb_documents")
    op.drop_table("processed_events")
    op.drop_table("enriched_tickets")
