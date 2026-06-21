#!/usr/bin/env python3
"""
Direct database migration script - creates tables without Alembic.
Run with: python migrate_db.py
"""
import asyncio
import sys
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Add app to path
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

from app.database.base import Base
from app.database.db import engine, async_session_maker
from app.models import User, CacheRule, APILog, RateLimitCounter, Analytics
from app.core.constants import UserRole
from passlib.context import CryptContext

# Import AsyncSessionLocal for seeding
AsyncSessionLocal = async_session_maker

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def migrate_db():
    """Create all tables and seed initial data."""
    try:
        print("🔄 Starting database migration...")
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables created successfully")
        
        # Seed default admin user
        async with AsyncSessionLocal() as session:
            try:
                # Check if admin exists
                from sqlalchemy import text
                result = await session.execute(
                    text("SELECT id FROM users WHERE email = :email"),
                    {"email": "admin@example.com"}
                )
                existing_admin = result.fetchone()
                
                if not existing_admin:
                    print("📝 Creating default admin user...")
                    admin_user = User(
                        username="admin",
                        email="admin@example.com",
                        hashed_password=pwd_context.hash("change-me-in-production"),
                        role=UserRole.ADMIN,
                        is_active=True,
                        is_superuser=True,
                        api_quota=100000
                    )
                    session.add(admin_user)
                    await session.commit()
                    print("✅ Admin user created: admin@example.com / change-me-in-production")
                else:
                    print("✅ Admin user already exists")
            except Exception as seed_error:
                print(f"⚠️  Warning: Could not seed admin user: {seed_error}")
                print("   (Tables were created successfully, you can create users manually via API)")
        
        print("\n✅ Database migration completed successfully!")
        print("\n📊 Created tables:")
        print("  - users")
        print("  - cache_rules")
        print("  - api_logs")
        print("  - rate_limit_counters")
        print("  - analytics")
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify MySQL is running: mysql -u root -p")
        print("  2. Create database: CREATE DATABASE api_optimizer;")
        print("  3. Update .env with correct credentials")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(migrate_db())
    sys.exit(0 if result else 1)
