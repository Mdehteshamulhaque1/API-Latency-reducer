"""Baseline schema: users, cache_rules, api_logs, analytics.

This revision describes the schema that existed before Alembic was
introduced. Each CREATE is guarded with an "exists" check so the migration
is safe on a fresh database AND on a database that was created earlier by
``Base.metadata.create_all``.

Revision ID: 0001
Revises:
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    existing = _existing_tables()

    if "users" not in existing:
        op.create_table(
            "users",
            *_base_columns(),
            sa.Column("username", sa.String(100), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            # Columns dropped again in revision 0002; kept here so the
            # baseline matches what create_all produced historically.
            sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("api_quota", sa.Integer(), nullable=False, server_default="10000"),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.create_index("idx_user_email", "users", ["email"])
        op.create_index("idx_user_active", "users", ["is_active"])

    if "cache_rules" not in existing:
        op.create_table(
            "cache_rules",
            *_base_columns(),
            sa.Column("endpoint_pattern", sa.String(255), nullable=False),
            sa.Column("ttl", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("cache_by_user", sa.Boolean(), nullable=False),
            sa.Column("cache_by_query_params", sa.Boolean(), nullable=False),
            sa.Column("cache_by_headers", sa.Boolean(), nullable=False),
            sa.Column("max_cache_size", sa.Integer(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
        )
        op.create_index("ix_cache_rules_id", "cache_rules", ["id"])
        op.create_index("ix_cache_rules_endpoint_pattern", "cache_rules", ["endpoint_pattern"])
        op.create_index("idx_cache_rule_endpoint", "cache_rules", ["endpoint_pattern"])
        op.create_index("idx_cache_rule_enabled", "cache_rules", ["enabled"])

    if "api_logs" not in existing:
        op.create_table(
            "api_logs",
            *_base_columns(),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("method", sa.String(10), nullable=False),
            sa.Column("endpoint", sa.String(500), nullable=False),
            sa.Column("path", sa.String(500), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("response_time_ms", sa.Float(), nullable=False),
            sa.Column("cache_hit", sa.Boolean(), nullable=False),
            sa.Column("cache_key", sa.String(500), nullable=True),
            sa.Column("client_ip", sa.String(45), nullable=False),
            sa.Column("correlation_id", sa.String(36), nullable=False),
            sa.Column("request_size_bytes", sa.Integer(), nullable=False),
            sa.Column("response_size_bytes", sa.Integer(), nullable=False),
            sa.Column("query_params", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
        )
        op.create_index("ix_api_logs_id", "api_logs", ["id"])
        op.create_index("ix_api_logs_user_id", "api_logs", ["user_id"])
        op.create_index("ix_api_logs_endpoint", "api_logs", ["endpoint"])
        op.create_index("ix_api_logs_status_code", "api_logs", ["status_code"])
        op.create_index("ix_api_logs_client_ip", "api_logs", ["client_ip"])
        op.create_index("ix_api_logs_correlation_id", "api_logs", ["correlation_id"])
        op.create_index("idx_api_log_user", "api_logs", ["user_id"])
        op.create_index("idx_api_log_endpoint", "api_logs", ["endpoint"])
        op.create_index("idx_api_log_status", "api_logs", ["status_code"])
        op.create_index("idx_api_log_created", "api_logs", ["created_at"])
        op.create_index("idx_api_log_correlation", "api_logs", ["correlation_id"])

    if "analytics" not in existing:
        op.create_table(
            "analytics",
            *_base_columns(),
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
        op.create_index("ix_analytics_id", "analytics", ["id"])
        op.create_index("ix_analytics_user_id", "analytics", ["user_id"])
        op.create_index("idx_analytics_user", "analytics", ["user_id"])
        op.create_index("idx_analytics_period", "analytics", ["period"])
        op.create_index("idx_analytics_created", "analytics", ["created_at"])


def downgrade() -> None:
    for table in ("analytics", "api_logs", "cache_rules", "users"):
        op.drop_table(table)
