"""Add guardrail_events, documents, and document_chunks.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns() -> list:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "guardrail_events" not in existing:
        op.create_table(
            "guardrail_events",
            *_base_columns(),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("correlation_id", sa.String(36), nullable=True),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("severity", sa.String(10), nullable=False, server_default="low"),
            sa.Column("feature", sa.String(30), nullable=False, server_default="chat"),
            sa.Column("detail", sa.String(255), nullable=False, server_default=""),
            sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_guardrail_events_id", "guardrail_events", ["id"])
        op.create_index("ix_guardrail_events_user_id", "guardrail_events", ["user_id"])
        op.create_index("ix_guardrail_events_correlation_id", "guardrail_events", ["correlation_id"])
        op.create_index("ix_guardrail_events_category", "guardrail_events", ["category"])
        op.create_index("idx_guardrail_created", "guardrail_events", ["created_at"])
        op.create_index("idx_guardrail_category_created", "guardrail_events", ["category", "created_at"])

    if "documents" not in existing:
        op.create_table(
            "documents",
            *_base_columns(),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(100), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("error_message", sa.String(255), nullable=True),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("character_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("flag_detail", sa.String(255), nullable=True),
            sa.Column("embedding_model", sa.String(100), nullable=True),
        )
        op.create_index("ix_documents_id", "documents", ["id"])
        op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
        op.create_index("ix_documents_content_hash", "documents", ["content_hash"], unique=True)
        op.create_index("ix_documents_status", "documents", ["status"])

    if "document_chunks" not in existing:
        op.create_table(
            "document_chunks",
            *_base_columns(),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("character_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("vector_id", sa.String(64), nullable=False),
        )
        op.create_index("ix_document_chunks_id", "document_chunks", ["id"])
        op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
        op.create_index("ix_document_chunks_vector_id", "document_chunks", ["vector_id"], unique=True)
        op.create_index("idx_chunk_document_position", "document_chunks", ["document_id", "position"])


def downgrade() -> None:
    for table in ("document_chunks", "documents", "guardrail_events"):
        op.drop_table(table)
