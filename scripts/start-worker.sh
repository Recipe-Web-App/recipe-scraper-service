#!/bin/bash
# ==============================================================================
# ARQ Worker Entrypoint Script
# ==============================================================================
# This script starts the ARQ background worker.
# ==============================================================================

set -euo pipefail

export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "=============================================="
echo "Recipe Scraper Worker"
echo "=============================================="
echo "Environment: ${ENVIRONMENT:-production}"
echo "Log Level: ${LOG_LEVEL}"
echo "=============================================="

# Start ARQ worker
exec arq app.workers.arq.WorkerSettings
