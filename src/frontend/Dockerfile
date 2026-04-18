# =============================================================================
# Multi-stage Dockerfile for Angular Frontend
# Supports both development (with hot reload) and production builds
# =============================================================================

# -----------------------------------------------------------------------------
# Base stage: Common Node.js setup
# -----------------------------------------------------------------------------
FROM node:22-alpine AS base

WORKDIR /app

# -----------------------------------------------------------------------------
# Dependencies stage: Install node_modules
# -----------------------------------------------------------------------------
FROM base AS dependencies

# Copy package files first for better layer caching
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for Angular CLI)
RUN npm ci

# -----------------------------------------------------------------------------
# Development stage: Hot reload enabled
# -----------------------------------------------------------------------------
FROM base AS development

WORKDIR /app

# Copy node_modules from dependencies stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy package files (for npm scripts)
COPY package.json package-lock.json ./

# Expose Angular dev server port
EXPOSE 4200

# Environment variables for hot reload in Docker
ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true
# Disable Angular analytics prompts
ENV NG_CLI_ANALYTICS=false

# Start Angular dev server with:
# - host 0.0.0.0 to accept connections from outside container
# - poll for file changes (required for Docker volume mounts on macOS/Windows)
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--poll", "2000"]

# -----------------------------------------------------------------------------
# Build stage: Production build
# -----------------------------------------------------------------------------
FROM dependencies AS build

# Copy source code
COPY . .

# Build for production
RUN npm run build -- --configuration=production

# -----------------------------------------------------------------------------
# Production stage: Serve with nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from build stage
COPY --from=build /app/dist/app/browser /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
