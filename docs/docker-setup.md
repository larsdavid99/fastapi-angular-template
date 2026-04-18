# Docker Development Setup

## Overview

Full-stack containerized development environment with hot reload support for all services.

## Architecture

```
┌─────────────────────────────────────────────┐
│                docker-compose                │
├─────────────────┬───────────────────────────┤
│    frontend     │        backend            │
│    :4200        │        :8000              │
│    Angular      │        FastAPI            │
│    hot reload   │       hot reload          │
│                 │        :5678 (debugpy)    │
└─────────────────┴───────────────────────────┘
```

## Services

| Service | Port | Technology | Hot Reload |
|---------|------|------------|------------|
| Frontend | 4200 | Angular 21+ | Polling (2s) |
| Backend | 8000 | FastAPI + Uvicorn | Native |
| Backend Debug | 5678 | debugpy remote attach | N/A |

## Quick Start

```bash
# Start all services
docker compose up --build

# Start in background
docker compose up -d --build

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

## Dockerfiles

### Frontend Dockerfile (`src/frontend/Dockerfile`)

Multi-stage build supporting development and production:

- **Development**: Uses `ng serve` with polling for hot reload
- **Production**: Nginx serving static files with SPA routing

Key features:
- Node 22 Alpine base image
- Analytics disabled (`NG_CLI_ANALYTICS=false`)
- File polling enabled for Docker volume mounts
- Production stage with nginx and gzip compression

### Backend Dockerfile (`src/backend/Dockerfile`)

Multi-stage build for FastAPI:

- **Development**: Uvicorn with `--reload` flag
- **Production**: Uvicorn without reload

Key features:
- Python 3.13 slim base image
- Hot reload via uvicorn file watching
- debugpy support for remote debugging on port 5678

## Hot Reload

### Frontend Hot Reload

Angular uses polling for file change detection (required for Docker volumes on macOS/Windows):

```dockerfile
ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--poll", "2000"]
```

Changes to files in `src/frontend/src/` trigger automatic browser refresh.

### Backend Hot Reload

Uvicorn watches for file changes natively, wrapped in debugpy:

```dockerfile
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

Changes to any Python file in `src/backend/` trigger automatic server restart.

## Node Modules Strategy

The frontend uses a **named Docker volume** for `node_modules`:

```yaml
volumes:
  - frontend_node_modules:/app/node_modules
```

**Why?**
- Prevents host/container platform conflicts (macOS vs Linux binaries)
- Better performance than bind mounts
- Survives container restarts

**When to rebuild:**
```bash
# After changing package.json or package-lock.json
docker compose down -v
docker compose up --build
```

## Common Commands

### Service Management

```bash
# Start all services
docker compose up --build

# Start specific service
docker compose up frontend --build

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v

# Restart a service
docker compose restart frontend

# Rebuild without cache
docker compose build --no-cache
```

### Logs

```bash
# All logs
docker compose logs -f

# Specific service
docker compose logs -f frontend
docker compose logs -f backend
```

### Shell Access

```bash
# Backend shell
docker compose exec backend bash

# Frontend shell
docker compose exec frontend sh
```

## Environment Variables

### Backend Environment

Set in `docker-compose.yml` or via `.env` file in `src/backend/`:

```bash
ENVIRONMENT=development
DEBUG=True
# Add project-specific keys as needed
```

### Frontend Environment

Angular environments are baked into the build. For runtime configuration, use `assets/env.js` pattern.

## Troubleshooting

### Frontend not loading

1. Check container is running: `docker compose ps`
2. Check logs: `docker compose logs frontend`
3. Verify Angular compiled: Look for "Application bundle generation complete"

### Hot reload not working

1. Verify polling is enabled in environment
2. Check volume mounts are correct
3. On macOS, ensure Docker has file sharing permissions

### Backend API errors

1. Check backend logs: `docker compose logs backend`
2. Verify required env vars are set
3. Check the API docs at http://localhost:8000/docs for endpoint details

### Node modules issues

```bash
# Reset node_modules volume
docker compose down -v
docker compose up --build frontend
```

### Port conflicts

```bash
# Check what's using a port
lsof -i :4200
lsof -i :8000

# Kill process or change ports in docker-compose.yml
```

## Accessing Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |
| Backend Docs | http://localhost:8000/docs |
| Backend Health | http://localhost:8000/health |
