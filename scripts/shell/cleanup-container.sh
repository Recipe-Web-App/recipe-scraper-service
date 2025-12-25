#!/bin/bash
# scripts/containerManagement/cleanup-scraper-container.sh

set -euo pipefail

NAMESPACE="recipe-scraper"
CONFIG_DIR="k8s"
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
echo "🧪 Checking Minikube status..."
print_separator "-"

if ! minikube status >/dev/null 2>&1; then
  echo "⚠️ Minikube is not running. Starting Minikube..."
  if ! minikube start; then
    echo "❌ Failed to start Minikube. Exiting."
    exit 1
  fi
else
  echo "✅ Minikube is already running."
fi

print_separator "="
echo "🧹 Deleting Kubernetes resources in namespace '$NAMESPACE'..."
print_separator "-"

kubectl delete -f "${CONFIG_DIR}/configmap-template.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/deployment.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/pod-disruption-budget.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/network-policy.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/secret-template.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/service.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/gateway-route.yaml" -n "$NAMESPACE" --ignore-not-found

print_separator "="
echo "🐳 Removing Docker image '${FULL_IMAGE_NAME}' from Minikube..."
print_separator "-"

eval "$(minikube docker-env)"
docker rmi -f "$FULL_IMAGE_NAME" || echo "Image not found or already removed."

print_separator "="
read -r -p "🛑 Do you want to stop (shut down) Minikube now? (y/N): " stop_mk
print_separator "-"

if [[ "$stop_mk" =~ ^[Yy]$ ]]; then
  echo "📴 Stopping Minikube..."
  minikube stop
  echo "✅ Minikube stopped."
else
  echo "🟢 Minikube left running."
fi

print_separator "="
echo "✅ Cleanup complete for namespace '$NAMESPACE'."
print_separator "="
