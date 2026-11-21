"""People using a monitored service, for the admin user directory.

``end_users`` maps an opaque end-user reference (``esone:7``) to the display
name and email the service sends with that person's questions.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "end_users" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "end_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ref", sa.String(100), nullable=False),
        sa.Column("service", sa.String(50), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_end_users_id", "end_users", ["id"])
    op.create_index("ix_end_users_ref", "end_users", ["ref"], unique=True)
    op.create_index("ix_end_users_service", "end_users", ["service"])


def downgrade() -> None:
    op.drop_index("ix_end_users_service", table_name="end_users")
    op.drop_index("ix_end_users_ref", table_name="end_users")
    op.drop_index("ix_end_users_id", table_name="end_users")
    op.drop_table("end_users")
