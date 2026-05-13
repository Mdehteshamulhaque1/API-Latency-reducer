#!/usr/bin/env python
"""Database migration script for API Optimizer."""

import sys
import os
from alembic.config import Config
from alembic import command

def init_migrations():
    """Initialize migrations."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "sqlite:///./test.db"))
    return config


def migrate(target='head'):
    """Apply migrations to database."""
    config = init_migrations()
    try:
        if target == 'head':
            command.upgrade(config, 'head')
            print("✅ Database migrated to latest version")
        else:
            command.upgrade(config, target)
            print(f"✅ Database migrated to {target}")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


def rollback(steps=1):
    """Rollback migrations."""
    config = init_migrations()
    try:
        for _ in range(steps):
            command.downgrade(config, '-1')
        print(f"✅ Rolled back {steps} migration(s)")
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        sys.exit(1)


def create_migration(message):
    """Create a new migration."""
    config = init_migrations()
    try:
        command.revision(config, autogenerate=True, message=message)
        print(f"✅ Migration created: {message}")
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        sys.exit(1)


def show_history():
    """Show migration history."""
    config = init_migrations()
    try:
        command.history(config)
    except Exception as e:
        print(f"❌ Failed to show history: {e}")
        sys.exit(1)


def show_current():
    """Show current database version."""
    config = init_migrations()
    try:
        command.current(config)
    except Exception as e:
        print(f"❌ Failed to show current version: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [command] [args]")
        print()
        print("Commands:")
        print("  migrate [target]    - Apply migrations (default: head)")
        print("  rollback [steps]    - Rollback migrations (default: 1)")
        print("  create [message]    - Create new migration")
        print("  history             - Show migration history")
        print("  current             - Show current version")
        print()
        print("Examples:")
        print("  python migrate.py migrate")
        print("  python migrate.py migrate 002")
        print("  python migrate.py rollback 2")
        print("  python migrate.py create 'Add new column'")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'migrate':
        target = sys.argv[2] if len(sys.argv) > 2 else 'head'
        migrate(target)
    elif command == 'rollback':
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        rollback(steps)
    elif command == 'create':
        message = sys.argv[2] if len(sys.argv) > 2 else 'Auto migration'
        create_migration(message)
    elif command == 'history':
        show_history()
    elif command == 'current':
        show_current()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
