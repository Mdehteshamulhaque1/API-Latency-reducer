"""Drop unused schema: rate_limit_counters table, users.is_superuser, users.api_quota.

Rate limiting lives in Redis (token buckets), so the SQL counter table was
never read or written. ``is_superuser`` duplicated ``role == "admin"`` and
``api_quota`` was never enforced. Batch mode lets SQLite drop columns by
rebuilding the table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _user_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("users")}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "rate_limit_counters" in inspector.get_table_names():
        op.drop_table("rate_limit_counters")

    columns = _user_columns()
    with op.batch_alter_table("users") as batch_op:
        if "is_superuser" in columns:
            batch_op.drop_column("is_superuser")
        if "api_quota" in columns:
            batch_op.drop_column("api_quota")


def downgrade() -> None:
    columns = _user_columns()
    with op.batch_alter_table("users") as batch_op:
        if "is_superuser" not in columns:
            batch_op.add_column(
                sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if "api_quota" not in columns:
            batch_op.add_column(
                sa.Column("api_quota", sa.Integer(), nullable=False, server_default="10000")
            )
    # The rate_limit_counters table is not recreated: nothing ever used it.
