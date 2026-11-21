"""Per-person request rows for monitored services.

``api_logs.end_user`` carries the end-user reference (``esone:7``) a
monitored service attaches to the requests a signed-in person made, so the
admin dashboard can show that person's own API activity.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("api_logs")}
    if "end_user" in columns:
        return
    op.add_column("api_logs", sa.Column("end_user", sa.String(100), nullable=True))
    op.create_index("idx_api_log_end_user_created", "api_logs", ["end_user", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_api_log_end_user_created", table_name="api_logs")
    op.drop_column("api_logs", "end_user")
