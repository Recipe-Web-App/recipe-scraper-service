#!/bin/bash
# scripts/shell/stop-container.sh

set -euo pipefail

NAMESPACE="recipe-scraper"
DEPLOYMENT="recipe-scraper"

print_separator() {
  printf '%*s\n' "${COLUMNS:-80}" '' | tr ' ' '='
}

# Check if Minikube is running
if ! minikube status | grep -q "Running"; then
  print_separator
  echo "🚀 Starting Minikube..."
  print_separator
  minikube start
fi

print_separator
echo "🛑 Scaling deployment '$DEPLOYMENT' in namespace '$NAMESPACE' to 0 replicas..."
print_separator

kubectl scale deployment "$DEPLOYMENT" --replicas=0 -n "$NAMESPACE"

print_separator
echo "✅ Deployment stopped."
print_separator
