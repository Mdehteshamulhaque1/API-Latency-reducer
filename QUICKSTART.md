# API Optimizer - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Local Development (Recommended for Learning)

#### Step 1: Clone and Setup

```bash
cd backend
python -m venv venv

# Activate venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### Step 2: Configure Environment

```bash
cp .env.example .env

# Edit .env - minimum requirements:
# DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/api_optimizer
# REDIS_URL=redis://localhost:6379/0
# SECRET_KEY=your-secret-key-32-chars-or-more
```

#### Step 3: Start MySQL and Redis

```bash
# Using Docker (easiest)
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=api_optimizer mysql:8.0
docker run -d -p 6379:6379 redis:7-alpine

# Or use your local installation
mysql -u root -p
> CREATE DATABASE api_optimizer;

# Redis usually starts automatically
redis-cli ping  # Should return PONG
```

#### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 5: Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

✅ **Server running at http://localhost:8000**

### Option 2: Docker Compose (Production-Like)

```bash
# From project root
docker-compose up -d

# Verify all services running
docker-compose ps

# Check logs
docker-compose logs -f backend
```

✅ **All services running in containers**

---

## 📚 First Steps

### 1. Access API Documentation

Open browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### 2. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "email": "demo@example.com",
    "password": "DemoPassword123!",
    "role": "viewer"
  }'
```

### 3. Login and Get Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "DemoPassword123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJSZWZyZXNo...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 4. Use the Token

```bash
# Save token
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# Get analytics
curl -X GET "http://localhost:8000/api/v1/analytics/summary?hours=24" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Create a Cache Rule

```bash
curl -X POST "http://localhost:8000/api/v1/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_pattern": "/api/users",
    "ttl": 3600,
    "enabled": true,
    "cache_by_user": true,
    "description": "Cache user endpoint"
  }'
```

---

## 📊 Key Features Demo

### Check Health

```bash
curl http://localhost:8000/api/v1/health
```

### Rate Limiting Test

Make 101 requests rapidly (limit is 100/hour):

```bash
for i in {1..102}; do
  curl -X GET "http://localhost:8000/api/v1/health"
  echo "Request $i"
done
```

Request 101 returns 429 (Too Many Requests)

### Analytics Summary

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/summary?hours=24" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 Configuration Reference

| Setting | Default | Purpose |
|---------|---------|---------|
| `DEBUG` | False | Enable debug mode |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `REDIS_CACHE_TTL` | 3600 | Default cache lifetime (seconds) |
| `RATE_LIMIT_ENABLED` | True | Enable/disable rate limiting |
| `RATE_LIMIT_DEFAULT_REQUESTS` | 100 | Requests per period |
| `RATE_LIMIT_DEFAULT_PERIOD` | 3600 | Time period (seconds) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT expiration |
| `CORS_ORIGINS` | ["http://localhost:3000"] | Allowed CORS origins |

---

## 🐛 Troubleshooting

### Issue: "Database connection refused"

```
Error: Can't connect to MySQL
```

**Solution:**
```bash
# Check MySQL is running
mysql -u root -p

# Or use Docker
docker run -d -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=api_optimizer \
  mysql:8.0
```

### Issue: "Redis connection refused"

```
Error: Redis connection error
```

**Solution:**
```bash
# Check Redis is running
redis-cli ping

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Issue: "Import errors after installing packages"

```bash
# Reinstall packages
pip install --force-reinstall -r requirements.txt

# Or clear cache
pip cache purge
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

```bash
# Use different port
uvicorn app.main:app --port 8001

# Or kill process on port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/              # API routes
│   ├── core/                # Core utilities
│   ├── middleware/          # Request middleware
│   ├── models/              # Database models
│   ├── schemas/             # Request/response schemas
│   ├── services/            # Business logic
│   ├── database/            # DB connection
│   ├── utils/               # Utilities
│   ├── tasks/               # Celery tasks
│   ├── config.py            # Configuration
│   └── main.py              # App entry point
├── tests/                   # Unit & integration tests
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image
└── README.md                # This file
```

---

## 📝 Example Workflows

### Workflow 1: Test Caching

```bash
TOKEN="your-token-here"

# Create cache rule
curl -X POST "http://localhost:8000/api/v1/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_pattern": "/api/data",
    "ttl": 3600
  }'

# Response will include rule ID (e.g., 1)

# Check rule
curl -X GET "http://localhost:8000/api/v1/rules/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Workflow 2: Monitor Analytics

```bash
TOKEN="your-token-here"

# Get summary for last 24 hours
curl -X GET "http://localhost:8000/api/v1/analytics/summary?hours=24" \
  -H "Authorization: Bearer $TOKEN"

# Get specific endpoint logs
curl -X GET "http://localhost:8000/api/v1/analytics/endpoints?endpoint_pattern=/api/users" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🚀 Next Steps

1. **Read Architecture Doc:** See `ARCHITECTURE.md`
2. **Explore API:** Open http://localhost:8000/docs
3. **Setup Frontend:** See `frontend/README.md` (if exists)
4. **Deploy to Production:** See deployment section in main README

---

## 💡 Tips & Best Practices

- ✅ Always validate `.env` before starting
- ✅ Use Swagger UI to test endpoints
- ✅ Monitor logs for errors: `docker-compose logs backend`
- ✅ Keep Redis running for cache features
- ✅ Use strong SECRET_KEY in production
- ✅ Enable HTTPS in production
- ✅ Configure backup for MySQL database
- ✅ Monitor rate limit usage

---

## Need Help?

- 📖 Full docs: See `README.md`
- 🏗️ Architecture: See `ARCHITECTURE.md`
- 🔗 API Docs: Open `http://localhost:8000/docs`
- 💬 Issues: Check GitHub issues
