"""INR token billing per answer on answer_logs.

Adds billable tokens and the INR charge for a request. Cache hits keep zeros;
existing non-cached rows are backfilled at 5 INR per token.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = [
    sa.Column("billable_tokens", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("cost_inr", sa.Float(), nullable=False, server_default="0"),
]


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("answer_logs")}
    for column in NEW_COLUMNS:
        if column.name not in existing:
            op.add_column("answer_logs", column)
    op.execute(
        "UPDATE answer_logs SET billable_tokens = total_tokens, cost_inr = total_tokens * 5.0 "
        "WHERE status = 'ok' AND cache_status NOT IN ('exact_hit', 'semantic_hit')"
    )


def downgrade() -> None:
    with op.batch_alter_table("answer_logs") as batch:
        batch.drop_column("cost_inr")
        batch.drop_column("billable_tokens")
