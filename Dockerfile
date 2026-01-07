# syntax=docker/dockerfile:1
# ==============================================================================
# Recipe Scraper Service - Multi-stage Production Dockerfile
# ==============================================================================
# Build arguments for flexibility
ARG PYTHON_VERSION=3.14
ARG UV_VERSION=0.5

# ==============================================================================
# Stage 1: Base Python image with UV
# ==============================================================================
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM python:${PYTHON_VERSION}-slim AS base

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # UV settings
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # App settings
    APP_HOME=/app

WORKDIR $APP_HOME

# ==============================================================================
# Stage 2: Builder - Install dependencies
# ==============================================================================
FROM base AS builder

# Copy UV from official image
COPY --from=uv /uv /usr/local/bin/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ==============================================================================
# Stage 3: Production image
# ==============================================================================
FROM base AS production

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appgroup $APP_HOME/.venv $APP_HOME/.venv

# Add venv to PATH
ENV PATH="$APP_HOME/.venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup src/ $APP_HOME/src/
COPY --chown=appuser:appgroup scripts/ $APP_HOME/scripts/

# Make scripts executable
RUN chmod +x "${APP_HOME}/scripts/"*.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - can be overridden
CMD ["scripts/entrypoint.sh"]

# ==============================================================================
# Stage 4: Development image (includes dev dependencies)
# ==============================================================================
FROM base AS development

# Copy UV from official image
COPY --from=uv /uv /usr/local/bin/uv

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy all project files
COPY . .

# Install all dependencies including dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Add venv to PATH
ENV PATH="$APP_HOME/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
