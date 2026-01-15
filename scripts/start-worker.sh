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

# Start ARQ worker using Python to properly handle event loop (Python 3.12+ fix)
exec python -c "
import asyncio

# Create and set event loop before importing arq (Python 3.12+ compatibility)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from arq import run_worker
from app.workers.arq import WorkerSettings

run_worker(WorkerSettings)
"
