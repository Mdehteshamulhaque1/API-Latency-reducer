"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_username'),
        sa.UniqueConstraint('email', name='uq_email'),
        sa.Index('idx_username', 'username'),
        sa.Index('idx_email', 'email'),
    )

    # Create api_logs table
    op.create_table(
        'api_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('endpoint_path', sa.String(500), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('correlation_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_user_id', 'user_id'),
        sa.Index('idx_endpoint', 'endpoint_path'),
        sa.Index('idx_method', 'method'),
        sa.Index('idx_status', 'status_code'),
        sa.Index('idx_created_at', 'created_at'),
    )

    # Create cache_rules table
    op.create_table(
        'cache_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint_pattern', sa.String(500), nullable=False),
        sa.Column('ttl', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('cache_by_user', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('cache_by_query_params', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('cache_by_headers', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('max_cache_size', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('idx_user_id', 'user_id'),
        sa.Index('idx_endpoint', 'endpoint_pattern'),
        sa.Index('idx_enabled', 'enabled'),
    )

    # Create rate_limit_counters table
    op.create_table(
        'rate_limit_counters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(255), nullable=False),
        sa.Column('counter', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reset_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('identifier', name='uq_identifier'),
        sa.Index('idx_reset_at', 'reset_at'),
    )

    # Create analytics table
    op.create_table(
        'analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_hits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_misses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('idx_user_id', 'user_id'),
        sa.Index('idx_period', 'period_start', 'period_end'),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('analytics')
    op.drop_table('rate_limit_counters')
    op.drop_table('cache_rules')
    op.drop_table('api_logs')
    op.drop_table('users')
