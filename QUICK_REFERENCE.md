# Quick Reference Guide

## 🚀 Common Commands

### Backend

#### Start Development Server
```bash
cd smart-api-optimizer
python -m uvicorn app.main:app --reload
```

#### Install Dependencies
```bash
cd smart-api-optimizer
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

#### Run Tests
```bash
cd smart-api-optimizer
pytest tests/
```

#### Start with Docker
```bash
cd smart-api-optimizer
docker-compose up -d
```

#### View API Documentation
http://localhost:8000/docs (Swagger)
http://localhost:8000/redoc (ReDoc)

---

### Frontend

#### Install Dependencies
```bash
cd frontend
npm install
```

#### Start Development Server
```bash
cd frontend
npm run dev
```

#### Build for Production
```bash
cd frontend
npm run build
```

#### Preview Production Build
```bash
cd frontend
npm run preview
```

#### Type Checking
```bash
cd frontend
npm run type-check
```

---

## 🔐 Default Credentials

**Username:** demo_user
**Password:** DemoPassword123!

---

## 📍 URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| MySQL | localhost:3306 |
| Redis | localhost:6379 |

---

## 🔑 API Endpoints Quick Reference

### Authentication
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
```

### Health
```
GET /api/v1/health
```

### Analytics
```
GET /api/v1/analytics/summary
GET /api/v1/analytics/endpoints/{endpoint_path}
```

### Cache Rules
```
GET /api/v1/rules
POST /api/v1/rules
GET /api/v1/rules/{rule_id}
PUT /api/v1/rules/{rule_id}
DELETE /api/v1/rules/{rule_id}
```

---

## 📊 Request Examples

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo_user", "password": "DemoPassword123!"}'
```

### Get Analytics Summary
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/summary?hours=24" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Cache Rule
```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "endpoint_pattern": "/api/users/*",
    "ttl": 3600,
    "enabled": true,
    "cache_by_user": true
  }'
```

---

## 🛠️ Environment Variables

### Backend (.env)
```
DATABASE_URL=mysql+aiomysql://root:password@localhost/api_optimizer
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
LOG_LEVEL=INFO
DEBUG=True
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

---

## 🐛 Troubleshooting

### Backend Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process
fuser -k 8000/tcp  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Then restart
python -m uvicorn app.main:app --reload
```

### Frontend Won't Start
```bash
# Clear node_modules
rm -rf node_modules  # Linux/Mac
rmdir /s /q node_modules  # Windows

# Reinstall
npm install

# Start again
npm run dev
```

### Database Connection Error
```bash
# Verify MySQL is running
# Verify credentials in .env
# Verify DATABASE_URL is correct
# Check MySQL port (default 3306)
```

### Redis Connection Error
```bash
# Verify Redis is running
# Verify REDIS_URL in .env
# Check Redis port (default 6379)
```

---

## 📈 Performance Tips

1. **Backend Caching**
   - Configure TTL for frequently accessed endpoints
   - Use cache by user/params/headers for better hit rates

2. **Frontend Optimization**
   - Use React Query for intelligent server state caching
   - Component lazy loading via React Router

3. **Database**
   - Indexes on frequently queried columns
   - Connection pooling enabled

4. **General**
   - Use gzip compression
   - Enable HTTP caching headers
   - Minimize payload sizes

---

## 🧪 Testing

### Backend Tests
```bash
cd smart-api-optimizer
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/ -v             # Verbose output
```

### Frontend Tests
```bash
cd frontend
npm test                      # Run tests
npm test -- --coverage        # With coverage report
```

---

## 📦 Deployment

### Docker Compose (Production)
```bash
cd smart-api-optimizer
docker-compose -f docker-compose.yml up -d
```

### Build Frontend for Production
```bash
cd frontend
npm run build
# Creates dist/ folder
serve -s dist -l 3000
```

### Build Backend Docker Image
```bash
cd smart-api-optimizer
docker build -t api-optimizer:1.0 .
docker run -p 8000:8000 api-optimizer:1.0
```

---

## 📚 Documentation Files

- `GETTING_STARTED.md` - Main setup guide
- `FRONTEND_SETUP.md` - Frontend installation
- `PROJECT_COMPLETION_REPORT.md` - Full project status
- `FRONTEND_COMPLETION_SUMMARY.md` - Frontend details
- `smart-api-optimizer/ARCHITECTURE.md` - Backend architecture
- `smart-api-optimizer/README.md` - Backend documentation
- `smart-api-optimizer/QUICKSTART.md` - Backend quick start
- `frontend/README.md` - Frontend documentation

---

## 🔄 Development Workflow

1. **Make changes** to code
2. **Backend auto-reloads** (uvicorn --reload)
3. **Frontend auto-reloads** (HMR via Vite)
4. **Verify** in browser/API docs
5. **Commit** changes

---

## 📞 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Port already in use | Kill process on that port |
| Module not found | Check Python path, reinstall packages |
| CORS error | Verify CORS_ORIGINS in backend config |
| API timeout | Check backend is running, increase timeout |
| Database error | Check MySQL is running, verify credentials |
| Redis error | Check Redis is running on port 6379 |
| 401 Unauthorized | Token expired, login again or use refresh endpoint |
| npm install fails | Clear npm cache: `npm cache clean --force` |

---

## 🎯 Quick Checklist

- [ ] Backend running on :8000?
- [ ] Frontend running on :3000?
- [ ] MySQL running?
- [ ] Redis running?
- [ ] Can login with demo credentials?
- [ ] Can see analytics on dashboard?
- [ ] Can create cache rules?
- [ ] Can view API docs at /docs?

---

## 🆘 Getting Help

1. Check documentation files
2. Review error messages carefully
3. Check browser console (frontend)
4. Check terminal output (backend)
5. Review inline code comments
6. Check API docs at http://localhost:8000/docs

---

**Last Updated:** 2024
**Version:** 1.0.0
