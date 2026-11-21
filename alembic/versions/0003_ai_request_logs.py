"""Add ai_request_logs: one row per LLM call (tokens, latency, estimated cost, outcome).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "ai_request_logs" in sa.inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        "ai_request_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.Column("feature", sa.String(30), nullable=False, server_default="chat"),
        sa.Column("provider", sa.String(30), nullable=False, server_default="openai"),
        sa.Column("requested_model", sa.String(100), nullable=True),
        sa.Column("served_model", sa.String(100), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(60), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ai_request_logs_id", "ai_request_logs", ["id"])
    op.create_index("ix_ai_request_logs_user_id", "ai_request_logs", ["user_id"])
    op.create_index("ix_ai_request_logs_correlation_id", "ai_request_logs", ["correlation_id"])
    op.create_index("ix_ai_request_logs_served_model", "ai_request_logs", ["served_model"])
    op.create_index("ix_ai_request_logs_outcome", "ai_request_logs", ["outcome"])
    op.create_index("idx_ai_log_created", "ai_request_logs", ["created_at"])
    op.create_index("idx_ai_log_user_created", "ai_request_logs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("ai_request_logs")
