"""Attribute request-log rows to a service and a direction.

``api_logs`` gains ``service`` (which application the row belongs to),
``direction`` ("inbound" for requests it served, "outbound" for calls it
made) and ``upstream_host`` (the target of an outbound call). Existing rows
are this service's own inbound traffic, which the server defaults express.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("api_logs")}
    if "service" not in columns:
        op.add_column(
            "api_logs",
            sa.Column("service", sa.String(50), nullable=False, server_default="api-optimizer"),
        )
    if "direction" not in columns:
        op.add_column(
            "api_logs",
            sa.Column("direction", sa.String(10), nullable=False, server_default="inbound"),
        )
    if "upstream_host" not in columns:
        op.add_column("api_logs", sa.Column("upstream_host", sa.String(255), nullable=True))
    indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("api_logs")}
    if "ix_api_logs_service" not in indexes:
        op.create_index("ix_api_logs_service", "api_logs", ["service"])
    if "idx_api_log_service_created" not in indexes:
        op.create_index("idx_api_log_service_created", "api_logs", ["service", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_api_log_service_created", table_name="api_logs")
    op.drop_index("ix_api_logs_service", table_name="api_logs")
    with op.batch_alter_table("api_logs") as batch:
        batch.drop_column("upstream_host")
        batch.drop_column("direction")
        batch.drop_column("service")
