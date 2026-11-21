"""Token and cost accounting per request on answer_logs.

Adds the cache status (exact_hit, semantic_hit, miss, bypassed), prompt,
completion and embedding tokens, embedding latency, the LLM and embedding
cost of the request, the total actual cost, the estimated cost a cache hit
saved, and whether the request waited for another request's generation
(stampede protection). Existing rows keep zeros; ``estimated_cost_usd``
stays as the total for older readers.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = [
    sa.Column("cache_status", sa.String(12), nullable=False, server_default="miss"),
    sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("embedding_tokens", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("embedding_ms", sa.Float(), nullable=False, server_default="0"),
    sa.Column("llm_cost_usd", sa.Float(), nullable=False, server_default="0"),
    sa.Column("embedding_cost_usd", sa.Float(), nullable=False, server_default="0"),
    sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0"),
    sa.Column("saved_cost_usd", sa.Float(), nullable=False, server_default="0"),
    sa.Column("waited_for_generation", sa.Boolean(), nullable=False, server_default=sa.false()),
]


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("answer_logs")}
    for column in NEW_COLUMNS:
        if column.name not in existing:
            op.add_column("answer_logs", column)
    # Older rows: cache hits were recorded with match_method; map them to a status.
    op.execute(
        "UPDATE answer_logs SET cache_status = CASE "
        "WHEN match_method = 'exact' THEN 'exact_hit' "
        "WHEN match_method IN ('embedding', 'lexical') THEN 'semantic_hit' "
        "ELSE 'miss' END "
        "WHERE cache_status = 'miss'"
    )
    op.execute("UPDATE answer_logs SET total_cost_usd = estimated_cost_usd, llm_cost_usd = estimated_cost_usd WHERE total_cost_usd = 0")
    indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("answer_logs")}
    if "idx_answer_log_cache_status_created" not in indexes:
        op.create_index("idx_answer_log_cache_status_created", "answer_logs", ["cache_status", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_answer_log_cache_status_created", table_name="answer_logs")
    with op.batch_alter_table("answer_logs") as batch:
        for column in reversed(NEW_COLUMNS):
            batch.drop_column(column.name)
