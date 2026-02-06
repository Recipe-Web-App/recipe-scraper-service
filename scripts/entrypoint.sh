#!/bin/bash
# ==============================================================================
# Application Entrypoint Script
# ==============================================================================
# This script serves as the main entrypoint for the API container.
# It handles:
# - Environment validation
# - Signal handling for graceful shutdown
# - Starting the application with proper configuration
# ==============================================================================

set -euo pipefail

# Default configuration
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"
export WORKERS="${WORKERS:-4}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Print startup information
echo "=============================================="
echo "Recipe Scraper Service"
echo "=============================================="
echo "Environment: ${ENVIRONMENT:-production}"
echo "Host: ${HOST}:${PORT}"
echo "Workers: ${WORKERS}"
echo "Log Level: ${LOG_LEVEL}"
echo "=============================================="

# Start the application with gunicorn
exec gunicorn app.main:app \
  --bind "${HOST}:${PORT}" \
  --workers "${WORKERS}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --log-level "${LOG_LEVEL,,}" \
  --access-logfile - \
  --error-logfile - \
  --timeout 120 \
  --keep-alive 5 \
  --graceful-timeout 30
