# =============================================================================
# Multi-stage Dockerfile for FastAPI Backend
# Supports both development (with hot reload) and production builds
# =============================================================================

# -----------------------------------------------------------------------------
# Base stage: Python with system dependencies
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS base

WORKDIR /app

# -----------------------------------------------------------------------------
# Development stage: Hot reload enabled
# -----------------------------------------------------------------------------
FROM base AS development

# Install runtime + dev deps (pytest, black, flake8) for in-container testing
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Expose FastAPI port
EXPOSE 8000

# Start uvicorn via debugpy so VS Code can attach on port 5678
# - debugpy listens on 0.0.0.0:5678 for VS Code remote attach
# - uvicorn runs with hot reload as normal
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
# Production stage: Optimized for deployment
# -----------------------------------------------------------------------------
FROM base AS production

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start uvicorn without reload for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
