# Docker Setup for Frontend

## Overview

The frontend is now fully containerized using Docker multi-stage builds for both development and production environments.

## Docker Configuration

### Dockerfile Structure
- **Base Stage**: Node.js 20 Alpine image
- **Development Stage**: Full dev environment with hot reload
- **Build Stage**: Optimized build process
- **Production Stage**: Nginx-served static files

### Key Features
- ✅ Multi-stage build for optimization
- ✅ Development hot reload support
- ✅ Production-ready Nginx configuration
- ✅ Volume mounting for live code changes
- ✅ Proper port configuration (3000)
- ✅ Environment variable support

## Quick Start

### Run the entire application stack:
```bash
# From project root
./scripts/docker-dev.sh
```

Or manually:
```bash
# Development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Production mode
docker-compose up --build
```

### Run only the frontend:
```bash
cd frontend
docker build -t finance-frontend .
docker run -p 3000:3000 finance-frontend
```

## Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Environment Variables

The frontend accepts these environment variables:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME="Finance Tracker"
VITE_APP_VERSION="1.0.0"
VITE_ENABLE_DEVTOOLS=true
NODE_ENV=development
```

## Development Features

- **Hot Reload**: Code changes are automatically reflected
- **Volume Mounting**: Live editing without rebuilding
- **Dev Tools**: React Query DevTools enabled
- **Source Maps**: Full debugging support
- **Fast Refresh**: React Fast Refresh enabled

## Production Features

- **Nginx**: High-performance static file serving
- **Gzip Compression**: Optimized asset delivery
- **Client-side Routing**: SPA routing support
- **Asset Caching**: Optimized browser caching
- **Security Headers**: Production security headers

## Docker Commands

### Build specific stage:
```bash
# Development build
docker build --target dev -t finance-frontend:dev .

# Production build
docker build --target production -t finance-frontend:prod .
```

### View logs:
```bash
# All services
docker-compose logs -f

# Frontend only
docker-compose logs -f frontend
```

### Clean up:
```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Troubleshooting

### Port Conflicts
If port 3000 is in use, update `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Change host port
```

### File Changes Not Reflecting
Ensure volume mounting is working:
```yaml
volumes:
  - ./frontend:/app
  - /app/node_modules
```

### Build Errors
Clear Docker cache and rebuild:
```bash
docker-compose build --no-cache frontend
```