# API Optimizer - Backend

Production-grade FastAPI application for API performance optimization, caching management, and analytics.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Testing](#testing)
5. [Database Migrations](#database-migrations)
6. [API Documentation](#api-documentation)
7. [Deployment](#deployment)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL 8.0+ (or SQLite for development)
- Redis 7.0+ (optional, for caching)

### Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Apply database migrations:**
   ```bash
   python migrate.py migrate
   ```

5. **Start development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

Server runs at: http://localhost:8000

---

## ✨ Features

### 🔐 Authentication & Security
- JWT token-based authentication
- Password hashing with bcrypt
- Refresh token rotation
- Role-based access control

### 📊 Analytics & Monitoring
- Real-time API metrics
- Request logging with correlation tracking
- Performance analytics
- Cache hit/miss ratios
- Error tracking

### 💾 Intelligent Caching
- Redis-backed caching layer
- TTL-based cache invalidation
- Conditional caching (by user, params, headers)
- Cache statistics and monitoring
- Automatic cleanup

### ⚡ Rate Limiting
- Token bucket algorithm
- Per-user rate limiting
- Per-IP rate limiting
- Configurable limits
- Redis-backed counters

### 🔄 Background Jobs
- Celery task queue
- Automatic cache cleanup
- Log aggregation
- Analytics computation
- Scheduled tasks with Celery Beat

### 📈 Database
- SQLAlchemy 2.0 async ORM
- MySQL with connection pooling
- 5 optimized tables
- Indexes on hot paths
- Relationship management

---

## 🏗️ Architecture

### Directory Structure

```
app/
├── main.py                      # FastAPI entry point
├── config.py                    # Configuration management
├── core/
│   ├── security.py             # JWT & password hashing
│   ├── exceptions.py           # Custom exceptions
│   └── constants.py            # Constants
├── middleware/
│   ├── auth.py                 # JWT validation
│   ├── rate_limit.py           # Rate limiting
│   ├── correlation_id.py       # Request tracking
│   └── metrics.py              # Performance metrics
├── models/                      # ORM models
│   ├── user.py
│   ├── api_log.py
│   ├── cache_rule.py
│   ├── rate_limit_counter.py
│   └── analytics.py
├── schemas/                     # Pydantic validation
│   ├── auth.py
│   ├── rules.py
│   └── analytics.py
├── services/                    # Business logic
│   ├── auth.py                 # Authentication
│   ├── cache.py                # Caching logic
│   ├── rate_limit.py           # Rate limiting
│   └── analytics.py            # Analytics
├── api/v1/                      # API routes
│   ├── auth.py                 # Auth endpoints
│   ├── health.py               # Health check
│   ├── analytics.py            # Analytics endpoints
│   └── rules.py                # Cache rules
├── database/                    # Database setup
│   ├── db.py                   # Session management
│   └── base.py                 # Base model
├── utils/                       # Utilities
│   ├── logger.py               # JSON logging
│   └── redis_client.py         # Redis wrapper
└── tasks/                       # Background jobs
    ├── cache_cleanup.py
    └── analytics.py
```

### Middleware Pipeline

```
Request
  ↓
[Correlation ID] → Adds tracking ID
  ↓
[Metrics] → Records timing
  ↓
[Rate Limit] → Checks limit
  ↓
[Auth] → Validates token
  ↓
[Route Handler]
  ↓
[Cache Check] → Returns cached if available
  ↓
[Database Query]
  ↓
[Cache Store] → Saves result
  ↓
Response
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/
```

### Run Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
pytest tests/integration/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Test Files

- `test_security.py` - Password hashing and JWT tokens
- `test_auth_service.py` - Authentication service
- `test_cache_service.py` - Caching logic
- `test_rate_limit_service.py` - Rate limiting
- `test_auth_endpoints.py` - Auth API endpoints
- `test_api_endpoints.py` - All API endpoints

### Test Statistics

- **Total Tests:** 63+
- **Unit Tests:** 33
- **Integration Tests:** 30+
- **Coverage:** > 80%

See `TESTING_AND_MIGRATIONS.md` for detailed testing guide.

---

## 🗄️ Database Migrations

### Apply Migrations

```bash
python migrate.py migrate
```

### Rollback Migrations

```bash
python migrate.py rollback
```

### Create New Migration

```bash
python migrate.py create "Description of change"
```

### View Migration Status

```bash
python migrate.py current    # Current version
python migrate.py history    # All versions
```

### Migration Files

- `alembic/versions/001_initial_migration.py` - Creates 5 tables

**Tables:**
1. **users** - User accounts
2. **api_logs** - Request logs
3. **cache_rules** - Cache configuration
4. **rate_limit_counters** - Rate limit tracking
5. **analytics** - Metrics aggregation

See `TESTING_AND_MIGRATIONS.md` for complete migration guide.

---

## 📚 API Documentation

### Base URL

```
http://localhost:8000/api/v1
```

### Authentication Endpoints

#### Register
```http
POST /auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "Password123!"
}
```

Response: `201 Created`
```json
{
  "id": 1,
  "username": "newuser",
  "email": "user@example.com",
  "is_active": true
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "newuser",
  "password": "Password123!"
}
```

Response: `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Analytics Endpoints

#### Get Summary
```http
GET /analytics/summary?hours=24
Authorization: Bearer <access_token>
```

Response: `200 OK`
```json
{
  "total_requests": 1500,
  "cache_hit_rate": 75.2,
  "avg_response_time_ms": 45.3,
  "error_rate": 0.5
}
```

#### Get Endpoint Logs
```http
GET /analytics/endpoints/{endpoint_path}?hours=24
Authorization: Bearer <access_token>
```

### Cache Rules Endpoints

#### List Rules
```http
GET /rules
Authorization: Bearer <access_token>
```

#### Create Rule
```http
POST /rules
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "endpoint_pattern": "/api/users/*",
  "ttl": 3600,
  "enabled": true,
  "cache_by_user": false
}
```

#### Update Rule
```http
PUT /rules/{rule_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "ttl": 7200,
  "enabled": true
}
```

#### Delete Rule
```http
DELETE /rules/{rule_id}
Authorization: Bearer <access_token>
```

### Interactive API Docs

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t api-optimizer:latest .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=mysql+aiomysql://user:pass@db:3306/api_optimizer \
  -e REDIS_URL=redis://redis:6379 \
  api-optimizer:latest
```

### Docker Compose

```bash
docker-compose up -d
```

Services:
- FastAPI: http://localhost:8000
- MySQL: localhost:3306
- Redis: localhost:6379

---

## ⚙️ Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=mysql+aiomysql://root:password@localhost/api_optimizer

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-super-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Logging
LOG_LEVEL=INFO
DEBUG=False

# Cache
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=1000

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_HOUR=1000
```

---

## 📊 Performance Metrics

- **Request Latency:** < 100ms (with caching)
- **Cache Hit Rate:** 60-80% (configurable)
- **Throughput:** 1000+ RPS (single instance)
- **Memory Usage:** ~200MB (with Redis)

---

## 🔒 Security Features

✅ JWT token authentication
✅ Password hashing with bcrypt
✅ CORS protection
✅ Rate limiting
✅ SQL injection prevention
✅ XSS protection
✅ Request validation
✅ Correlation ID tracking

---

## 🐛 Troubleshooting

### Database Connection Error

```bash
# Check MySQL is running
# Verify DATABASE_URL in .env
# Check MySQL credentials
```

### Redis Connection Error

```bash
# Check Redis is running
# Verify REDIS_URL in .env
# Check Redis port (default 6379)
```

### Tests Failing

```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/unit/test_security.py::TestPasswordHashing::test_hash_password -v

# Check error message carefully
```

### Migration Error

```bash
# Check current version
python migrate.py current

# View migration history
python migrate.py history

# Rollback if needed
python migrate.py rollback
```

---

## 📈 Development Workflow

1. **Make code changes**
2. **Run tests:** `pytest tests/`
3. **Check coverage:** `pytest tests/ --cov=app`
4. **Format code:** `black app/`
5. **Lint code:** `flake8 app/`
6. **Commit changes** with test coverage > 80%

---

## 📚 Documentation

- [Testing & Migrations Guide](TESTING_AND_MIGRATIONS.md)
- [System Architecture](ARCHITECTURE.md)
- [Quick Start Guide](QUICKSTART.md)
- [Testing Summary](TESTING_IMPLEMENTATION_SUMMARY.md)

---

## 🚀 Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Coverage > 80%
- [ ] Migrations applied
- [ ] Environment variables set
- [ ] Database backed up
- [ ] Redis configured
- [ ] SSL certificates ready

### Deploy

```bash
# Build and push image
docker build -t api-optimizer:1.0 .
docker push myregistry/api-optimizer:1.0

# Update deployment
kubectl apply -f deployment.yaml

# Verify
kubectl rollout status deployment/api-optimizer
```

---

## 📞 Support

- **API Docs:** http://localhost:8000/docs
- **Issues:** Check error logs in console/logs
- **Testing:** `pytest tests/ -v`
- **Migrations:** `python migrate.py current`

---

## 📄 License

MIT - See LICENSE file

---

## 🎉 Status

✅ Production Ready
✅ 63+ Tests Passing
✅ Database Migrations Setup
✅ Full API Documentation
✅ Docker Ready

**Version:** 1.0.0
**Last Updated:** 2024
