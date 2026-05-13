# API Optimizer - Frontend Setup Guide

## Prerequisites

- Node.js 18+ (download from https://nodejs.org/)
- npm 9+ (comes with Node.js)
- Backend running on http://localhost:8000

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Create Environment File

```bash
copy .env.example .env
```

Or manually create `.env`:
```
VITE_API_URL=http://localhost:8000
```

### 3. Start Development Server

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

### 4. Login with Demo Account

- **Username:** demo_user
- **Password:** DemoPassword123!

Or register a new account.

## Available Commands

### Development
```bash
npm run dev          # Start dev server with HMR
```

### Production Build
```bash
npm run build        # Build optimized bundle
npm run preview      # Preview production build locally
```

### Type Checking
```bash
npm run type-check   # Check TypeScript errors
```

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx              # Main app component with routing
│   ├── main.tsx             # React entry point
│   ├── index.css            # Global Tailwind styles
│   ├── components/          # Reusable UI components
│   │   ├── Navigation.tsx    # Header/navigation bar
│   │   ├── LoadingSpinner.tsx
│   │   ├── ErrorAlert.tsx
│   │   ├── Toast.tsx
│   │   ├── Badge.tsx
│   │   ├── Card.tsx
│   │   ├── Skeleton.tsx
│   │   └── useToast.tsx     # Toast hook
│   ├── pages/               # Page components
│   │   ├── LoginPage.tsx    # Authentication page
│   │   ├── RegisterPage.tsx # User registration
│   │   ├── DashboardPage.tsx # Main analytics dashboard
│   │   └── RulesPage.tsx    # Cache rules management
│   ├── services/            # API integration layer
│   │   ├── api.ts           # Axios instance with JWT
│   │   ├── auth.ts          # Auth service methods
│   │   └── api-services.ts  # Analytics & rules services
│   └── store/               # State management
│       └── index.ts         # Zustand auth store
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind CSS config
├── tsconfig.json            # TypeScript config
└── package.json             # Dependencies

```

## Features Implemented

### ✅ Authentication
- User registration and login
- JWT token management (access + refresh)
- Automatic token refresh
- Protected routes

### ✅ Analytics Dashboard
- Real-time metrics display
- Interactive charts (Recharts)
- Cache performance pie chart
- Top endpoints bar chart
- Response time analysis
- Endpoint performance table
- Time range filtering (1H, 6H, 24H, 7D)

### ✅ Cache Rules Management
- Create new cache rules
- Edit existing rules
- Delete rules
- Configure TTL
- Set caching options (by user, query params, headers)
- Real-time rule updates

### ✅ User Interface
- Modern Tailwind CSS design
- Responsive mobile-friendly layout
- Dark mode ready
- Interactive components
- Loading states
- Error handling

## Troubleshooting

### Issue: "Cannot find module" error
```bash
# Clear node_modules and reinstall
rm -rf node_modules
npm install
```

### Issue: API connection errors
1. Verify backend is running: http://localhost:8000/docs
2. Check `VITE_API_URL` in `.env` file
3. Ensure CORS is enabled in backend

### Issue: Port 3000 already in use
```bash
# Use different port
npm run dev -- --port 3001
```

### Issue: TypeScript errors
```bash
npm run type-check
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | http://localhost:8000 | Backend API base URL |
| `VITE_API_TIMEOUT` | 30000 | Request timeout in milliseconds |
| `VITE_DEBUG_API` | false | Enable API request logging |

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions

## Performance Tips

1. **Code Splitting:** Routes are automatically code-split
2. **Image Optimization:** Use WebP format when possible
3. **React Query DevTools:** Only loaded in development
4. **Bundle Size:** Vite produces optimized bundles (~100KB gzipped)

## Deployment

### Vercel (Recommended)
```bash
npm run build
# Push to git, connect to Vercel
```

### Docker
```bash
docker build -t api-optimizer-frontend .
docker run -p 3000:3000 api-optimizer-frontend
```

### Manual Server
```bash
npm run build
npm install -g serve
serve -s dist -l 3000
```

## Development Workflow

1. **Start Backend**
   ```bash
   cd smart-api-optimizer
   python -m uvicorn app.main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open Dashboard**
   - Navigate to http://localhost:3000
   - Login with demo account or create new account

4. **Make Changes**
   - Frontend changes auto-reload via HMR
   - Backend changes auto-reload via uvicorn reload

## API Integration

All API requests are automatically authenticated using JWT tokens. The axios interceptor in `src/services/api.ts` handles:
- Adding Authorization header
- Token refresh on expiration
- Error handling and retries

Example API call:
```typescript
import { analyticsService } from '@/services/api-services'

const { data } = useQuery(() => analyticsService.getSummary(24))
```

## State Management

### Zustand Store
```typescript
import { useAuthStore } from '@/store'

const { user, isAuthenticated, login, logout } = useAuthStore()
```

### React Query
```typescript
import { useQuery, useMutation } from 'react-query'

const { data, isLoading, error } = useQuery(key, fetcher)
```

## Contributing

1. Use TypeScript for type safety
2. Follow Tailwind naming conventions
3. Keep components small and focused
4. Use React Query for server state
5. Use Zustand for client state
6. Add error handling and loading states

## Support

- **Frontend Issues:** Check browser console for errors
- **Backend API Docs:** http://localhost:8000/docs
- **React Query DevTools:** Visible in development mode

## Next Steps

1. ✅ Frontend is ready to run
2. Ensure backend is running on http://localhost:8000
3. Start the dev server: `npm run dev`
4. Open http://localhost:3000
5. Login and explore the dashboard

## License

MIT - See LICENSE file in root
