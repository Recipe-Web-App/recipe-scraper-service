#!/bin/bash
# scripts/shell/stop-container.sh

set -euo pipefail

NAMESPACE="recipe-scraper"
DEPLOYMENT="recipe-scraper"

print_separator() {
  printf '%*s\n' "${COLUMNS:-80}" '' | tr ' ' '='
}

print_separator
echo "🛑 Scaling deployment '$DEPLOYMENT' in namespace '$NAMESPACE' to 0 replicas..."
print_separator

kubectl scale deployment "$DEPLOYMENT" --replicas=0 -n "$NAMESPACE"

print_separator
echo "✅ Deployment stopped."
print_separator
