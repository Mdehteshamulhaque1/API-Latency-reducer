# Alembic - Database Migration Tool

```
# Create a migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# View migration history
alembic history

# Current database version
alembic current
```
