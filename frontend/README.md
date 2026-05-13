# API Optimizer Frontend

Professional React dashboard for the API Optimizer system.

## Features

- **Authentication**
  - User registration and login
  - JWT token management
  - Protected routes

- **Analytics Dashboard**
  - Real-time metrics
  - Interactive charts (Recharts)
  - Cache performance visualization
  - Response time analysis
  - Endpoint performance tracking

- **Cache Rules Management**
  - Create, read, update, delete cache rules
  - Endpoint pattern configuration
  - Conditional caching options
  - TTL management

- **Professional UI**
  - Modern design with Tailwind CSS
  - Responsive layout
  - Real-time updates
  - Intuitive navigation

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **React Query** - Server state management
- **Zustand** - Client state management
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **Lucide Icons** - Icon library

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   ├── pages/           # Page components
│   ├── services/        # API integration
│   ├── store/           # Zustand stores
│   ├── types/           # TypeScript types
│   ├── utils/           # Utility functions
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
VITE_API_URL=http://localhost:8000
EOF
```

### Development

```bash
npm run dev
```

Server runs at `http://localhost:3000`

### Build

```bash
npm run build
```

## Usage

### Login

1. Go to http://localhost:3000
2. Click "Register" to create an account or use demo credentials:
   - Username: `demo_user`
   - Password: `DemoPassword123!`

### Dashboard

- View real-time analytics
- Monitor cache performance
- Track API metrics
- Filter by time range (1H, 6H, 24H, 7D)

### Cache Rules

- Create new cache rules for endpoints
- Configure TTL and caching options
- Enable/disable rules
- Monitor rule usage

## Key Components

### LoginPage
User authentication with form validation and error handling.

### RegisterPage
User registration with password confirmation.

### DashboardPage
Main analytics dashboard with:
- Key metrics cards
- Cache performance pie chart
- Top endpoints bar chart
- Response time analysis
- Endpoint performance table

### RulesPage
Cache rules management:
- List all rules
- Create new rules
- Edit existing rules
- Delete rules

### Navigation
Header navigation with user info and logout.

## API Integration

Services are organized by domain:
- `auth.ts` - Authentication endpoints
- `api-services.ts` - Analytics and rules endpoints

All requests are automatically authenticated with JWT tokens.

## State Management

### Authentication Store (Zustand)
```typescript
useAuthStore()
- accessToken
- refreshToken
- user
- isAuthenticated
- login()
- logout()
```

## Styling

Tailwind CSS with custom components:
- `.card` - Card container
- `.btn-primary` - Primary button
- `.btn-secondary` - Secondary button
- `.badge` - Badge element
- `.badge-success`, `.badge-warning`, `.badge-error` - Status badges

## Development Tips

1. **Hot Module Reload** - Changes reflect immediately
2. **React Query DevTools** - Debug server state in development
3. **TypeScript** - Full type safety for better DX
4. **Responsive** - Mobile-friendly by default

## Building for Production

```bash
# Build optimized bundle
npm run build

# Preview production build
npm run preview
```

## Deployment

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### Environment Variables

```
VITE_API_URL=https://api.example.com
```

## Common Issues

### CORS Errors
Ensure backend is running and CORS is configured:
```python
# backend/app/config.py
CORS_ORIGINS=["http://localhost:3000"]
```

### API Connection
Check proxy in `vite.config.ts` matches your backend URL.

### Build Errors
Clear node_modules and reinstall:
```bash
rm -rf node_modules
npm install
npm run build
```

## Contributing

Follow these guidelines:
1. Use TypeScript
2. Follow Tailwind naming conventions
3. Keep components small and focused
4. Use React Query for server state
5. Use Zustand for client state

## License

MIT - See LICENSE file in root

## Support

For issues and questions:
- Backend API docs: http://localhost:8000/docs
- Frontend error logs: Browser console
