# API Optimizer - Testing & Migration Guide

## 📋 Overview

This guide covers:
- ✅ Setting up tests
- ✅ Running unit tests
- ✅ Running integration tests
- ✅ Database migrations with Alembic
- ✅ Test coverage reporting

---

## 🧪 Testing Setup

### Prerequisites

Dependencies are already in `requirements.txt`:
```
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
pytest-cov==4.1.0
```

### Installation

```bash
cd smart-api-optimizer
pip install -r requirements.txt
```

---

## 📁 Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_security.py     # Password hashing and JWT tests
│   ├── test_auth_service.py # Authentication service tests
│   ├── test_cache_service.py # Caching logic tests
│   └── test_rate_limit_service.py # Rate limiting tests
└── integration/             # Integration tests
    ├── __init__.py
    ├── test_auth_endpoints.py # Auth API endpoint tests
    └── test_api_endpoints.py  # Other API endpoint tests
```

---

## 🧪 Running Tests

### Run All Tests

```bash
pytest tests/
```

Output:
```
tests/unit/test_security.py::TestPasswordHashing::test_hash_password PASSED
tests/unit/test_security.py::TestPasswordHashing::test_verify_password_correct PASSED
...
tests/integration/test_auth_endpoints.py::TestAuthEndpoints::test_login_success PASSED
...

================================ 45 passed in 2.34s ================================
```

### Run Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Run Integration Tests Only

```bash
pytest tests/integration/ -v
```

### Run Specific Test File

```bash
pytest tests/unit/test_security.py -v
```

### Run Specific Test Class

```bash
pytest tests/unit/test_security.py::TestPasswordHashing -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_security.py::TestPasswordHashing::test_hash_password -v
```

### Run with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only auth tests
pytest -m auth

# Run only database tests
pytest -m db
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

This generates:
- Terminal report showing coverage percentage
- HTML report in `htmlcov/index.html` (open in browser)

### Run Tests Script (Windows)

```bash
run_tests.cmd
```

### Run Tests Script (Linux/Mac)

```bash
bash run_tests.sh
```

---

## 🔧 Test Configuration

### pytest.ini

Configuration file at project root:
```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --strict-markers --tb=short -ra
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    db: Database tests
    auth: Authentication tests
    cache: Cache tests
    api: API endpoint tests
asyncio_mode = auto
```

### conftest.py

Shared fixtures for all tests:

```python
# In-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test client with database override
@pytest.fixture
def client(async_db_session):
    ...

# Test user
@pytest.fixture
async def test_user(async_db_session):
    ...

# Auth headers
@pytest.fixture
def auth_headers(test_user_token):
    ...
```

---

## ✅ Unit Tests

### Test Password Hashing (test_security.py)

```python
def test_hash_password():
    """Test password is hashed correctly."""
    password = "TestPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 20
    assert hashed.startswith("$2b$")  # bcrypt prefix
```

Tests:
- ✅ Password hashing with bcrypt
- ✅ Password verification (correct password)
- ✅ Password verification (wrong password)
- ✅ Unique hashes for same password

### Test JWT Tokens (test_security.py)

```python
def test_verify_access_token():
    """Test access token verification."""
    user_id = 1
    tokens = create_tokens(user_id)
    access_token = tokens["access_token"]
    
    payload = verify_token(access_token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
```

Tests:
- ✅ Token creation
- ✅ Access token verification
- ✅ Refresh token verification
- ✅ Invalid token handling
- ✅ Expired token handling

### Test Auth Service (test_auth_service.py)

```python
@pytest.mark.asyncio
async def test_authenticate_user_success():
    """Test successful user authentication."""
    service = AuthService(db_session)
    
    user = await service.authenticate_user(
        username="testuser",
        password="TestPassword123!"
    )
    
    assert user is not None
    assert user.username == "testuser"
```

Tests:
- ✅ User registration
- ✅ Duplicate username prevention
- ✅ User authentication (success/failure)
- ✅ Token creation
- ✅ Token refresh

### Test Cache Service (test_cache_service.py)

```python
def test_cache_key_includes_user_id():
    """Test cache key includes user ID when specified."""
    service = CacheService()
    
    key_with_user = service.compute_cache_key(
        endpoint="/api/users/1",
        cache_by_user=True,
        user_id=123
    )
    
    assert "123" in key_with_user
```

Tests:
- ✅ Cache key generation
- ✅ Different keys for different parameters
- ✅ User ID inclusion in keys
- ✅ Query params inclusion
- ✅ Headers inclusion

### Test Rate Limit Service (test_rate_limit_service.py)

```python
def test_rate_limit_key_for_user():
    """Test rate limit key generation for user."""
    service = RateLimitService()
    
    key = service._get_limit_key(user_id=123, ip="127.0.0.1")
    
    assert "123" in key
    assert "rate_limit" in key
```

Tests:
- ✅ Rate limit key for users
- ✅ Rate limit key for IPs
- ✅ Different keys for different identifiers

---

## 🌐 Integration Tests

### Test Auth Endpoints (test_auth_endpoints.py)

```python
def test_register_success(client):
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Password123!"
        }
    )
    
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
```

Tests:
- ✅ User registration
- ✅ Duplicate username prevention
- ✅ Invalid email handling
- ✅ Weak password detection
- ✅ User login
- ✅ Wrong password handling
- ✅ Token refresh

### Test API Endpoints (test_api_endpoints.py)

#### Health Check

```python
def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

#### Analytics Endpoints

```python
def test_get_analytics_summary_authorized(client, auth_headers):
    """Test analytics summary with authentication."""
    response = client.get(
        "/api/v1/analytics/summary?hours=24",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "cache_hit_rate" in data
```

Tests:
- ✅ Auth requirement verification
- ✅ Analytics summary
- ✅ Endpoint logs
- ✅ Invalid parameters

#### Rules Endpoints

```python
def test_create_rule_authorized(client, auth_headers):
    """Test creating rule with authentication."""
    response = client.post(
        "/api/v1/rules",
        headers=auth_headers,
        json={
            "endpoint_pattern": "/api/users/*",
            "ttl": 3600,
            "enabled": True
        }
    )
    
    assert response.status_code == 201
```

Tests:
- ✅ Auth requirement
- ✅ Create rule
- ✅ Invalid TTL handling
- ✅ Get rule by ID
- ✅ Update rule
- ✅ Delete rule

---

## 🗄️ Database Migrations

### Overview

Alembic handles database schema versioning:
- ✅ Track schema changes
- ✅ Apply/rollback migrations
- ✅ Auto-generate migrations
- ✅ Version control

### File Structure

```
alembic/
├── versions/           # Migration files
│   ├── 001_initial_migration.py
│   ├── 002_add_feature.py
│   └── ...
├── env.py             # Environment configuration
├── script.py.mako     # Migration template
└── README.md
```

### Migration Files

Each migration file contains:
```python
"""Migration description

Revision ID: 001
Revises: 
Create Date: 2024-01-01
"""

def upgrade() -> None:
    """Apply migration."""
    # SQL operations

def downgrade() -> None:
    """Rollback migration."""
    # Reverse SQL operations
```

---

## 📝 Running Migrations

### Setup Alembic (First Time)

Alembic is already configured. Just run migrations:

```bash
python migrate.py migrate
```

### Apply All Migrations

```bash
python migrate.py migrate
```

Or with Alembic directly:

```bash
alembic upgrade head
```

Output:
```
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume character set utf8mb4
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_migration
✅ Database migrated to latest version
```

### Apply Specific Migration

```bash
python migrate.py migrate 002
```

### Rollback Last Migration

```bash
python migrate.py rollback
```

### Rollback Multiple Migrations

```bash
python migrate.py rollback 3
```

### Create New Migration

```bash
python migrate.py create "Add new table"
```

Or with Alembic:

```bash
alembic revision --autogenerate -m "Add new table"
```

### Show Migration History

```bash
python migrate.py history
```

Or:

```bash
alembic history --oneline
```

Output:
```
001 -> Initial migration, 2024-01-01 00:00:00
```

### Show Current Database Version

```bash
python migrate.py current
```

Or:

```bash
alembic current
```

Output:
```
001_initial_migration (head)
```

---

## 🔄 Full Migration Workflow

### Step 1: Create Migration

```bash
python migrate.py create "Add user roles"
```

This creates new file: `alembic/versions/002_add_user_roles.py`

### Step 2: Edit Migration

```python
def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(50)))
    op.create_index('idx_role', 'users', ['role'])

def downgrade() -> None:
    op.drop_index('idx_role', 'users')
    op.drop_column('users', 'role')
```

### Step 3: Apply Migration

```bash
python migrate.py migrate
```

### Step 4: Verify

```bash
python migrate.py current
```

### Step 5: Rollback if Needed

```bash
python migrate.py rollback
```

---

## ⚠️ Migration Best Practices

1. **Always write down migrations**
   ```bash
   python migrate.py create "Descriptive message"
   ```

2. **Test migrations before committing**
   ```bash
   python migrate.py migrate      # Apply
   python migrate.py rollback      # Test rollback
   python migrate.py migrate       # Apply again
   ```

3. **Keep migrations atomic**
   - One logical change per migration
   - Add related changes together

4. **Write both upgrade and downgrade**
   - Always implement downgrade()
   - Test rollback functionality

5. **Use descriptive names**
   - Bad: `002_update_stuff.py`
   - Good: `002_add_user_roles_table.py`

6. **No destructive operations without confirmation**
   - Document breaking changes
   - Provide data migration script if needed

---

## 🐛 Testing Database

### Reset Test Database

Tests use in-memory SQLite by default (no manual reset needed).

### Use Real Database for Testing

To test with MySQL:

```python
# In conftest.py
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", 
    "mysql+aiomysql://root:password@localhost/test_api_optimizer")
```

### Database State Between Tests

Each test gets a fresh database session:

```python
@pytest.fixture
async def db_session(async_db_session):
    yield async_db_session
    # Automatically rolled back after test
```

---

## 📊 Coverage Reports

### Generate Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

### View HTML Report

```bash
# Linux/Mac
open htmlcov/index.html

# Windows
start htmlcov\index.html
```

### Coverage Goals

- Overall: > 80%
- Core services: > 90%
- Middleware: > 85%
- API routes: > 75%

---

## 🔍 Debugging Tests

### Run Tests with Output

```bash
pytest tests/ -s  # Show print statements
```

### Run Tests with Full Traceback

```bash
pytest tests/ --tb=long
```

### Run Single Test with Debug

```bash
pytest tests/unit/test_security.py::TestPasswordHashing::test_hash_password -s -vv
```

### Use PDB Debugger

```python
def test_something():
    breakpoint()  # Python 3.7+
    # Code execution pauses here
```

---

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: "3.10"
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run migrations
        run: |
          python migrate.py migrate
      
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## ✅ Pre-Commit Checklist

Before committing code:

- [ ] All tests pass: `pytest tests/`
- [ ] Coverage > 80%: `pytest tests/ --cov=app`
- [ ] No type errors: `mypy app/`
- [ ] Code formatted: `black app/`
- [ ] Lints pass: `flake8 app/`
- [ ] Migrations created: `python migrate.py history`

---

## 📞 Common Issues

### Issue: "No module named 'app'"

**Solution:**
```bash
# Make sure you're in the smart-api-optimizer directory
cd smart-api-optimizer
pytest tests/
```

### Issue: Database connection error

**Solution:**
```bash
# Check DATABASE_URL in .env
# Use in-memory SQLite for tests
TEST_DATABASE_URL="sqlite+aiosqlite:///:memory:"
```

### Issue: "Event loop is closed"

**Solution:**
```bash
# Use pytest-asyncio properly
pytest tests/ -p pytest_asyncio
```

### Issue: Migration conflicts

**Solution:**
```bash
# Check current version
python migrate.py current

# View history
python migrate.py history

# Merge migration files manually if needed
```

---

## 📚 Resources

- **Pytest Documentation:** https://docs.pytest.org
- **Alembic Documentation:** https://alembic.sqlalchemy.org
- **FastAPI Testing:** https://fastapi.tiangolo.com/advanced/testing-dependencies/
- **SQLAlchemy Async:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

---

## 🎯 Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Run tests: `pytest tests/`
3. ✅ Apply migrations: `python migrate.py migrate`
4. ✅ Start application: `python -m uvicorn app.main:app --reload`
5. ✅ View API docs: http://localhost:8000/docs

---

**Happy testing! 🚀**
