"""Per-caller detail on answer_logs.

Adds the end-user reference a monitored service passes with each question,
the request status (ok / error / blocked) and error code, the cache key
that served or stored the answer, the latency components (cache lookup,
model call), and the model usage (tokens, estimated cost, served model),
so every caller has a complete record even when the answer came from the
shared cache.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = [
    sa.Column("end_user", sa.String(100), nullable=True),
    sa.Column("status", sa.String(10), nullable=False, server_default="ok"),
    sa.Column("error_code", sa.String(60), nullable=True),
    sa.Column("cache_key", sa.String(80), nullable=True),
    sa.Column("cache_lookup_ms", sa.Float(), nullable=False, server_default="0"),
    sa.Column("llm_ms", sa.Float(), nullable=False, server_default="0"),
    sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
    sa.Column("served_model", sa.String(100), nullable=True),
]


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("answer_logs")}
    for column in NEW_COLUMNS:
        if column.name not in existing:
            op.add_column("answer_logs", column)
    indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("answer_logs")}
    if "ix_answer_logs_end_user" not in indexes:
        op.create_index("ix_answer_logs_end_user", "answer_logs", ["end_user"])
    if "idx_answer_log_end_user_created" not in indexes:
        op.create_index("idx_answer_log_end_user_created", "answer_logs", ["end_user", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_answer_log_end_user_created", table_name="answer_logs")
    op.drop_index("ix_answer_logs_end_user", table_name="answer_logs")
    with op.batch_alter_table("answer_logs") as batch:
        for column in reversed(NEW_COLUMNS):
            batch.drop_column(column.name)
