#!/usr/bin/env python3
"""
Apply database migrations and seed the initial admin user.

Run from the repository root:  python scripts/migrate_db.py

1. ``alembic upgrade head`` brings the schema to the latest revision. Safe
   on a fresh database and on one created earlier by create_all.
2. If no user exists with ADMIN_EMAIL, an admin account is created with
   ADMIN_PASSWORD. Existing passwords are never overwritten, because this
   script runs on every deploy.
"""
import asyncio
import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.config import settings  # noqa: E402
from app.core.constants import UserRole  # noqa: E402
from app.core.security import PasswordHandler  # noqa: E402
from app.database.db import async_session_maker, close_db  # noqa: E402
from app.models import User  # noqa: E402


def run_migrations() -> None:
    config = Config(os.path.join(ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    command.upgrade(config, "head")


async def seed_admin() -> None:
    """Create the admin user once; never reset an existing password."""
    try:
        async with async_session_maker() as session:
            existing = await session.execute(select(User).where(User.email == settings.admin_email))
            if existing.scalar_one_or_none() is not None:
                print(f"Admin user already exists ({settings.admin_email}); password left unchanged")
                return
            session.add(
                User(
                    username="admin",
                    email=settings.admin_email,
                    hashed_password=PasswordHandler.hash_password(settings.admin_password),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            await session.commit()
            print(f"Admin user created: {settings.admin_email} (password from ADMIN_PASSWORD)")
    finally:
        await close_db()


def main() -> int:
    try:
        print("Applying migrations (alembic upgrade head)...")
        run_migrations()
        print("Schema is up to date")
        asyncio.run(seed_admin())
        print("Database setup complete")
        return 0
    except SQLAlchemyError as exc:
        print(f"Database error: {exc}")
        print("Check DATABASE_URL in .env and that the database server is reachable.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
