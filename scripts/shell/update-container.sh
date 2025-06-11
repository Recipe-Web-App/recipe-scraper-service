#!/bin/bash
# scripts/shell/update-container.sh

set -euo pipefail

NAMESPACE="recipe-scraper"
DEPLOYMENT="recipe-scraper"
IMAGE_NAME="recipe-scraper-service"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Fixes bug where first separator line does not fill the terminal width
COLUMNS=$(tput cols 2>/dev/null || echo 80)

# Utility function for printing section separators
print_separator() {
  local char="${1:-=}"
  local width="${COLUMNS:-80}"
  printf '%*s\n' "$width" '' | tr ' ' "$char"
}

print_separator "="
echo "🔄 Setting up Minikube Docker environment..."
print_separator "-"
eval "$(minikube docker-env)"
echo "✅ Minikube environment setup successfully."

print_separator "="
echo "🐳 Building Docker image: ${FULL_IMAGE_NAME}"
print_separator "-"
docker build -t "${FULL_IMAGE_NAME}" .
echo "✅ Docker image '${FULL_IMAGE_NAME}' built successfully."

print_separator "="
echo "♻️  Restarting deployment '${DEPLOYMENT}' in namespace '${NAMESPACE}' to pick up new image..."
print_separator "-"
kubectl rollout restart deployment/"${DEPLOYMENT}" -n "${NAMESPACE}"

print_separator "="
echo "⏳ Waiting for rollout to finish..."
print_separator "-"
kubectl rollout status deployment/"${DEPLOYMENT}" -n "${NAMESPACE}"

print_separator "="
echo "✅ Update complete. The latest image is now running."
print_separator "-"
