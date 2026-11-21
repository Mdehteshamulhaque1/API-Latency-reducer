"""Drop the hourly analytics roll-up table.

The ``analytics`` table was written on every request but never read: every
dashboard number is computed from ``api_logs`` directly. Removing it takes a
SELECT and an UPDATE off the write path of each request.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "analytics" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("analytics")


def downgrade() -> None:
    op.create_table(
        "analytics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("period", sa.String(50), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("total_errors", sa.Integer(), nullable=False),
        sa.Column("cache_hits", sa.Integer(), nullable=False),
        sa.Column("cache_misses", sa.Integer(), nullable=False),
        sa.Column("avg_response_time_ms", sa.Float(), nullable=False),
        sa.Column("min_response_time_ms", sa.Float(), nullable=False),
        sa.Column("max_response_time_ms", sa.Float(), nullable=False),
        sa.Column("total_bytes_sent", sa.Integer(), nullable=False),
        sa.Column("total_bytes_received", sa.Integer(), nullable=False),
    )
