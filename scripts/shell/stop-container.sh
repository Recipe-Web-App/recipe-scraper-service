#!/bin/bash
# scripts/shell/stop-container.sh

set -euo pipefail

NAMESPACE="recipe-scraper"
DEPLOYMENT="recipe-scraper"

# Fixes bug where first separator line does not fill the terminal width
COLUMNS=$(tput cols 2>/dev/null || echo 80)

# Utility function for printing section separators
print_separator() {
  local char="${1:-=}"
  local width="${COLUMNS:-80}"
  printf '%*s\n' "$width" '' | tr ' ' "$char"
}

# Check if Minikube is running
if ! minikube status | grep -q "Running"; then
  print_separator "="
  echo "🚀 Starting Minikube..."
  print_separator "-"
  minikube start
fi

print_separator "="
echo "🛑 Scaling deployment '$DEPLOYMENT' in namespace '$NAMESPACE' to 0 replicas..."
print_separator "-"

kubectl scale deployment "$DEPLOYMENT" --replicas=0 -n "$NAMESPACE"

print_separator "="
echo "✅ Deployment stopped."
print_separator "="
