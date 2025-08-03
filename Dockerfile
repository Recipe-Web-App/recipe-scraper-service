# Multi-stage Docker build for Recipe Scraper Service
# Stage 1: Build dependencies and compile Python packages
FROM python:3.13-slim as builder

# Set build environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --only=main --no-root \
    && poetry build

# Stage 2: Runtime image
FROM python:3.13-slim as runtime

# Create non-root user for security
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /app/.venv /home/appuser/.venv

# Copy application code
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./config ./config
COPY --chown=appuser:appuser ./pyproject.toml .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp \
    && chown -R appuser:appuser /app

# Security: Remove sensitive package managers and tools
RUN apt-get remove -y curl \
    && apt-get autoremove -y \
    && apt-get clean

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/liveness', timeout=5)"

# Expose port
EXPOSE 8000

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Default command with security hardening
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log", \
     "--log-level", "info"]
