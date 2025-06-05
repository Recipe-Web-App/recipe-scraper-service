#!/bin/bash
# scripts/shell/start-container.sh

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
echo "🔄 Scaling deployment '$DEPLOYMENT' in namespace '$NAMESPACE' to 1 replica..."
print_separator

kubectl scale deployment "$DEPLOYMENT" --replicas=1 -n "$NAMESPACE"

print_separator
echo "⏳ Waiting for pod to be ready..."
print_separator

kubectl wait --namespace="$NAMESPACE" \
  --for=condition=Ready pod \
  --selector=app=recipe-scraper \
  --timeout=90s

print_separator
echo "✅ Deployment started."
print_separator
