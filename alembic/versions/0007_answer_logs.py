"""Record every asked question with its answer.

``answer_logs`` holds one row per POST /api/v1/answers call: the question,
the answer it received, whether it came from the semantic cache or the
crawler, which sources were used and how long it took. The dashboard's
"Answer cache" page and the most-asked ranking aggregate from here; the
Redis list ``answers:recent`` mirrors the newest hour for fast reads.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "answer_logs" in tables:
        return
    op.create_table(
        "answer_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_hash", sa.String(40), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answered_by", sa.String(10), nullable=False),
        sa.Column("found", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("match_method", sa.String(12), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("compose_method", sa.String(10), nullable=True),
        sa.Column("primary_source", sa.String(20), nullable=True),
        sa.Column("sources", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("crawl_ms", sa.Float(), nullable=True),
    )
    op.create_index("ix_answer_logs_id", "answer_logs", ["id"])
    op.create_index("ix_answer_logs_user_id", "answer_logs", ["user_id"])
    op.create_index("ix_answer_logs_correlation_id", "answer_logs", ["correlation_id"])
    op.create_index("ix_answer_logs_question_hash", "answer_logs", ["question_hash"])
    op.create_index("idx_answer_log_created", "answer_logs", ["created_at"])
    op.create_index("idx_answer_log_user_created", "answer_logs", ["user_id", "created_at"])
    op.create_index("idx_answer_log_hash_created", "answer_logs", ["question_hash", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_answer_log_hash_created", table_name="answer_logs")
    op.drop_index("idx_answer_log_user_created", table_name="answer_logs")
    op.drop_index("idx_answer_log_created", table_name="answer_logs")
    op.drop_index("ix_answer_logs_question_hash", table_name="answer_logs")
    op.drop_index("ix_answer_logs_correlation_id", table_name="answer_logs")
    op.drop_index("ix_answer_logs_user_id", table_name="answer_logs")
    op.drop_index("ix_answer_logs_id", table_name="answer_logs")
    op.drop_table("answer_logs")
