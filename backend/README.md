# API Optimizer - Production Grade Backend

## Overview

**API Optimizer** is a production-level API optimization system built with FastAPI, designed to minimize redundant API calls, improve response times, and provide intelligent caching and analytics.

### Key Features

✅ **Intelligent Caching**
- TTL-based caching with Redis
- Conditional caching (by user, query params, headers)
- Automatic cache invalidation

✅ **Rate Limiting**
- Token bucket algorithm
- Per-user and per-IP limits
- Configurable thresholds

✅ **API Analytics**
- Real-time request tracking
- Cache hit/miss ratios
- Response time analysis
- Error tracking

✅ **Authentication**
- JWT token-based auth
- Refresh tokens
- Role-based access control (Admin, Operator, Viewer)

✅ **Background Jobs**
- Celery-based task scheduling
- Cache cleanup
- Log aggregation
- Performance alerts

✅ **Production Ready**
- Structured logging
- Error handling with custom exceptions
- CORS support
- Docker containerization

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | FastAPI 0.104+ |
| **Async** | asyncio, uvicorn |
| **Database** | MySQL 8.0+, SQLAlchemy 2.0 |
| **Caching** | Redis 7.0+ |
| **Jobs** | Celery 5.3+ |
| **Auth** | JWT (python-jose) |
| **Validation** | Pydantic v2 |

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py          # Authentication endpoints
│   │       ├── health.py        # Health check
│   │       ├── analytics.py     # Analytics endpoints
│   │       └── rules.py         # Cache rules management
│   ├── core/
│   │   ├── constants.py         # App constants
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── security.py          # JWT & password utilities
│   ├── middleware/
│   │   ├── auth.py              # JWT middleware
│   │   ├── rate_limit.py        # Rate limiting
│   │   ├── correlation_id.py    # Request tracking
│   │   └── metrics.py           # Performance metrics
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic validation schemas
│   ├── services/                # Business logic layer
│   ├── database/                # DB connection & base model
│   ├── tasks/                   # Celery background tasks
│   ├── utils/                   # Utilities (logging, redis)
│   ├── config.py                # Configuration management
│   └── main.py                  # FastAPI app entry
├── tests/                       # Unit & integration tests
├── requirements.txt
└── Dockerfile
```

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Redis 7.0+
- Docker & Docker Compose (optional)

### Local Development Setup

#### 1. Clone & Setup Environment

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Copy environment file
cp .env.example .env

# Edit .env with your local credentials
nano .env
```

#### 2. Configure .env

```env
# Database
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/api_optimizer

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (change in production!)
SECRET_KEY=your-secret-key-min-32-chars-change-in-production

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Initialize Database

```bash
# Create MySQL database
mysql -u root -p
> CREATE DATABASE api_optimizer;
> EXIT;

# Run migrations (if using Alembic)
alembic upgrade head
```

#### 5. Start Services

**Terminal 1 - FastAPI Server:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Celery Worker (optional):**
```bash
celery -A app.tasks worker -l info
```

**Terminal 3 - Celery Beat (optional):**
```bash
celery -A app.tasks beat -l info
```

### Docker Setup (Recommended)

```bash
# From project root
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f backend
```

---

## API Documentation

### Base URL
- Local: `http://localhost:8000`
- Production: `https://api.example.com`

### API Prefix
All endpoints use: `/api/v1`

### Authentication

All protected endpoints require JWT token:
```
Authorization: Bearer <access_token>
```

---

## Core Endpoints

### Authentication

**Register User**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password_123",
  "role": "viewer"
}
```

**Login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password_123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNo...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Refresh Token**
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNo..."
}
```

### Health Check

```http
GET /api/v1/health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "healthy",
  "redis": "healthy"
}
```

### Cache Rules

**List Rules**
```http
GET /api/v1/rules?skip=0&limit=100
Authorization: Bearer <token>
```

**Create Rule**
```http
POST /api/v1/rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "endpoint_pattern": "/api/users/*",
  "ttl": 3600,
  "enabled": true,
  "cache_by_user": true,
  "cache_by_query_params": true,
  "max_cache_size": 1000,
  "priority": 1,
  "description": "Cache user endpoint for 1 hour"
}
```

**Update Rule**
```http
PUT /api/v1/rules/{rule_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "ttl": 7200,
  "enabled": false
}
```

### Analytics

**Get Summary**
```http
GET /api/v1/analytics/summary?hours=24
Authorization: Bearer <token>

Response:
{
  "total_requests": 1523,
  "total_errors": 12,
  "cache_hit_rate": 67.5,
  "avg_response_time_ms": 145.3,
  "slowest_endpoint": "/api/users/search",
  "slowest_response_time_ms": 2341.2,
  "error_rate": 0.78,
  "top_endpoints": [...]
}
```

---

## Configuration

### Environment Variables

```env
# App
APP_NAME=API Optimizer
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# Database
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
DATABASE_POOL_SIZE=20
DATABASE_POOL_RECYCLE=3600

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# JWT
SECRET_KEY=<min-32-chars-random-string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT_REQUESTS=100
RATE_LIMIT_DEFAULT_PERIOD=3600

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<secure-password>
```

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "value"
  }
}
```

### Common Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `AUTHENTICATION_ERROR` | 401 | Invalid/missing token |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `DATABASE_ERROR` | 500 | Database operation failed |

---

## Performance Tuning

### Database
- Connection pooling enabled (20 connections)
- Automatic connection recycling (3600s)
- Indexed queries for fast lookups

### Caching
- Redis for distributed caching
- TTL-based expiration
- Conditional caching reduces cache size

### Rate Limiting
- Token bucket algorithm (efficient)
- Per-user and per-IP tracking
- Redis-backed for distributed systems

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/unit/test_auth.py

# Run integration tests
pytest tests/integration/
```

---

## Deployment

### Production Checklist

- [ ] Change `DEBUG=False`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure production `DATABASE_URL`
- [ ] Setup Redis with authentication
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS_ORIGINS
- [ ] Setup monitoring/logging
- [ ] Configure backup strategy
- [ ] Test database failover
- [ ] Load test the system

### Docker Deployment

```bash
# Build image
docker build -t api-optimizer:latest backend/

# Run container
docker run -d \
  --name api-optimizer \
  -p 8000:8000 \
  --env-file .env \
  api-optimizer:latest
```

### Using Docker Compose

```bash
# Production setup
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f backend

# Scale workers
docker-compose up -d --scale celery=3
```

---

## Monitoring & Logging

### Structured Logging

All logs are JSON-formatted with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.services.auth",
  "message": "User authenticated",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123
}
```

### Metrics

- Request count
- Response time (min, max, avg, p95, p99)
- Cache hit rate
- Error rate by endpoint
- Database query time

---

## Contributing

1. Create feature branch
2. Follow PEP8 style guide
3. Write tests for new features
4. Submit pull request

---

## License

MIT License - See LICENSE file

---

## Support

For issues and questions:
- GitHub Issues: [link]
- Documentation: [link]
- Email: support@example.com
