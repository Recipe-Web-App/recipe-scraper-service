#!/bin/bash
# scripts/shell/get-container-status.sh

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

print_separator "="
echo "🔍 Checking Minikube status..."
print_separator "-"

if ! minikube status | grep -q "Running"; then
  echo "❌ Minikube is NOT running."
else
  echo "✅ Minikube is running."
fi

print_separator "="
echo "🔍 Checking Kubernetes deployment status for '$DEPLOYMENT' in namespace '$NAMESPACE'..."
print_separator "-"

if ! kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" >/dev/null 2>&1; then
  echo "❌ Deployment '$DEPLOYMENT' does NOT exist in namespace '$NAMESPACE'."
else
  replicas=$(kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" -o jsonpath='{.status.replicas}')
  ready_replicas=$(kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
  echo "✅ Deployment '$DEPLOYMENT' exists in namespace '$NAMESPACE'."
  echo "   Total replicas: $replicas"
  echo "   Ready replicas: $ready_replicas"
fi

print_separator "="
echo "✅ Status check complete."
print_separator "="
