# API Optimizer - Production Architecture

## System Architecture

The API Optimizer follows a **layered architecture** pattern designed for scalability and maintainability.

```
┌──────────────────────────────────────────────────────────────┐
│                   CLIENT LAYER (HTTP/REST)                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│              MIDDLEWARE LAYER (Request Processing)           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 1. Correlation ID Middleware (Request Tracking)       │  │
│  │ 2. Metrics Middleware (Performance Collection)        │  │
│  │ 3. Rate Limit Middleware (Request throttling)         │  │
│  │ 4. Auth Middleware (JWT Validation)                   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│            API LAYER (Route Handlers & Validation)           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ /api/v1/auth/        (Authentication)                 │  │
│  │ /api/v1/rules/       (Cache Rules)                    │  │
│  │ /api/v1/analytics/   (Metrics & Analytics)            │  │
│  │ /api/v1/health       (Health Check)                   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│         SERVICE LAYER (Business Logic & Orchestration)       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ AuthService       - User authentication & JWT          │  │
│  │ CacheService      - Intelligent cache management       │  │
│  │ RateLimitService  - Token bucket rate limiting         │  │
│  │ AnalyticsService  - Metrics aggregation & queries      │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│         DATA ACCESS LAYER (Database & Cache)                 │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ SQLAlchemy ORM                                         │  │
│  │ • User Model                                           │  │
│  │ • APILog Model (Request tracking)                      │  │
│  │ • CacheRule Model                                      │  │
│  │ • Analytics Model                                      │  │
│  │ • RateLimitCounter Model                               │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼──────────┐ ┌──▼──────────────┐
│ MySQL Database │ │ Redis Cache   │ │ Celery Tasks   │
│                │ │               │ │                │
│ • Users        │ │ • Sessions    │ │ • Cache cleanup│
│ • API Logs     │ │ • Cache data  │ │ • Log agg.     │
│ • Rules        │ │ • Rate limits │ │ • Alerts       │
│ • Analytics    │ │               │ │                │
└────────────────┘ └───────────────┘ └────────────────┘
```

---

## Dataflow

### Request Processing Pipeline

```
Incoming HTTP Request
        │
        ▼
┌──────────────────────┐
│ CorrelationIDMiddleware
│ (Add tracking ID)
└──────────────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ MetricsMiddleware
        │ (Start timer)
        └──────────┬───┘
                   │
                   ▼
            ┌─────────────┐
            │ RateLimitMiddleware
            │ (Check quota)
            └──────┬──────┘
                   │
              No ──┴── Yes
              │         │
              ▼         ▼
         429 Error  ┌──────────┐
                    │ AuthMiddleware
                    │ (Validate JWT)
                    └──────┬───┘
                           │
                      No ──┴── Yes
                      │         │
                      ▼         ▼
                   401 Error ┌────────────┐
                            │ Route Handler
                            │ (Business logic)
                            └────┬─────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │ CacheService
                          │ (Check cache)
                          └────┬──────┬─┘
                               │      │
                      Hit ──────┘      └────── Miss
                      │                       │
                      ▼                       ▼
                  Return cached       ┌──────────────┐
                  response            │ ExecuteLogic
                  │                   │ + Store cache
                  │                   └──────┬───────┘
                  │                         │
                  └──────────────┬──────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ MetricsMiddleware
                        │ (Log response time,
                        │  cache hit, etc)
                        └──────┬───────────┘
                               │
                               ▼
                     Return response to client
                               │
                               ▼
                    ┌─────────────────────────┐
                    │ AsyncAnalyticsService
                    │ (Background: Log to DB)
                    └─────────────────────────┘
```

---

## Key Design Patterns

### 1. **Dependency Injection**

All dependencies injected via FastAPI `Depends()`:

```python
@app.get("/items")
async def get_items(
    session: AsyncSession = Depends(get_session),
    redis: RedisClient = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    pass
```

**Benefits:**
- Easy testing (mock dependencies)
- Loose coupling
- Clear dependencies

### 2. **Service Layer Pattern**

Business logic isolated in services, routes remain thin:

```python
# Route (thin)
@router.post("/login")
async def login(credentials, session):
    auth_service = AuthService(session)
    return auth_service.authenticate(...)

# Service (thick)
class AuthService:
    async def authenticate(self, username, password):
        # Complex logic here
        pass
```

### 3. **Middleware Stack**

Request processing order matters:

```
CorrelationID → Metrics → RateLimit → Auth → Handler
```

### 4. **Error Handling**

Custom exceptions provide structured error responses:

```python
try:
    user = await auth_service.get_user(user_id)
except ResourceNotFoundError as e:
    # Automatically converted to JSON response
    raise HTTPException(status_code=404, detail=e.message)
```

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    api_quota INT DEFAULT 10000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### API Logs Table
```sql
CREATE TABLE api_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    method VARCHAR(10),
    endpoint VARCHAR(500),
    status_code INT,
    response_time_ms FLOAT,
    cache_hit BOOLEAN,
    client_ip VARCHAR(45),
    correlation_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_endpoint (endpoint),
    INDEX idx_status (status_code),
    INDEX idx_created (created_at)
);
```

### Cache Rules Table
```sql
CREATE TABLE cache_rules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    endpoint_pattern VARCHAR(255),
    ttl INT DEFAULT 3600,
    enabled BOOLEAN DEFAULT TRUE,
    cache_by_user BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_endpoint (endpoint_pattern)
);
```

---

## Caching Strategy

### Cache Key Generation

```
endpoint[:user_id][:params_hash][:headers_hash]

Examples:
- /api/users                    → endpoint-only caching
- /api/users:user:123          → per-user caching
- /api/users:params:a3f2b1     → per-query-params caching
- /api/users:user:123:params:a3f2b1:headers:x7y8z9  → conditional
```

### TTL Configuration

| Endpoint Type | Default TTL | Strategy |
|--------------|-------------|----------|
| User data | 1 hour | Per-user cached |
| Public data | 24 hours | Global cached |
| Real-time | 5 minutes | Short TTL |
| Search | 30 minutes | Query-param cached |

---

## Rate Limiting Algorithm

### Token Bucket

```
capacity = 100 requests per hour

Process:
1. On each request, increment counter
2. If counter > capacity → reject (429)
3. Reset counter every hour

Advantages:
- O(1) lookup time
- Redis-backed for scalability
- Per-user and per-IP support
```

---

## Authentication Flow

```
┌─────────────────┐
│ Credentials     │
│ (user + pass)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ POST /auth/login            │
│ Hash password + verify      │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Generate JWT tokens         │
│ • access_token (30 min)     │
│ • refresh_token (7 days)    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Return tokens to client     │
└─────────────────────────────┘

On subsequent requests:
┌──────────────────────────────┐
│ Include Authorization header │
│ Bearer <access_token>        │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ AuthMiddleware validates JWT │
│ Extract: user_id, role       │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Attach to request.state      │
│ Available in route handler   │
└──────────────────────────────┘
```

---

## Scalability Considerations

### Horizontal Scaling

```
┌────────────────────────────────────┐
│      Load Balancer (Nginx)         │
└───────┬──────────────────┬─────────┘
        │                  │
        ▼                  ▼
   ┌─────────┐        ┌─────────┐
   │ FastAPI │        │ FastAPI │  (Multiple instances)
   │ Server1 │        │ Server2 │
   └────┬────┘        └────┬────┘
        │                  │
        └──────┬───────────┘
               │
        ┌──────▼───────┐
        │ Redis Cluster │ (Shared cache)
        └───────┬──────┘
               │
        ┌──────▼───────┐
        │ MySQL Master │  (Primary DB)
        │ MySQL Slave  │  (Replica)
        └──────────────┘
```

### Optimization Tips

1. **Connection Pooling**
   - MySQL: 20-50 connections per instance
   - Redis: Single connection (async)

2. **Cache Warming**
   - Pre-populate frequently accessed data
   - Background refresh job

3. **Database Indexing**
   - Index on `created_at`, `user_id`, `endpoint`
   - Composite indexes for multi-column queries

4. **Async Operations**
   - Offload analytics logging to background tasks
   - Use Celery for heavy operations

---

## Security Measures

### Authentication
- ✅ Passwords hashed with bcrypt
- ✅ JWT tokens with expiration
- ✅ Refresh token rotation

### Authorization
- ✅ Role-based access control (RBAC)
- ✅ Admin/Operator/Viewer tiers

### API Security
- ✅ CORS validation
- ✅ Rate limiting (DoS protection)
- ✅ Input validation (Pydantic)
- ✅ SQL injection prevention (ORM)

### Infrastructure
- ✅ Environment variables for secrets
- ✅ No hardcoded credentials
- ✅ HTTPS enforcement (production)

---

## Monitoring & Observability

### Metrics Collected

- **Request metrics:**
  - Method, path, status code
  - Response time (ms)
  - Request size, response size

- **Cache metrics:**
  - Hit rate
  - Miss rate
  - Cache size

- **Rate limit metrics:**
  - Requests per user/IP
  - Rejected requests

- **Database metrics:**
  - Query time
  - Connection pool usage
  - Slow query logs

### Logging

All logs include:
- Timestamp (ISO 8601)
- Level (DEBUG, INFO, WARNING, ERROR)
- Logger name
- Message
- Correlation ID
- User ID (if authenticated)

---

## Performance Benchmarks

### Typical Performance (Production)

| Operation | Latency | Notes |
|-----------|---------|-------|
| Cache hit | 5-10ms | Redis lookup |
| Cache miss + DB | 50-150ms | Query + serialize |
| Auth check | 1-2ms | JWT decode |
| Rate limit check | 2-5ms | Redis increment |
| Overall p95 | <200ms | Full stack |

---

## Disaster Recovery

### Backup Strategy

- **Database:** Daily snapshots to S3
- **Redis:** RDB dump every hour
- **Logs:** Archived to cold storage

### Failover Procedures

1. **Database Failover:**
   - Replica promotion to master
   - Update connection string

2. **Redis Failover:**
   - Sentinel monitoring
   - Automatic failover to replica

3. **Application Failover:**
   - Traffic rerouted via load balancer
   - Health checks every 10s

---

## Future Enhancements

- [ ] GraphQL API
- [ ] WebSocket support for real-time analytics
- [ ] Machine learning for cache prediction
- [ ] Advanced query optimization
- [ ] Multi-region deployment
- [ ] Event streaming (Kafka)
