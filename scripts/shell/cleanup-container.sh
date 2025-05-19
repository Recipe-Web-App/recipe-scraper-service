#!/bin/bash
# scripts/containerManagement/cleanup-scraper-container.sh

set -euo pipefail

NAMESPACE="recipe-scraper"
CONFIG_DIR="k8s"
CLUSTER_NAME="recipe-manager-system"
IMAGE_NAME="recipe-scraper-service:latest"

# Utility function for printing section separators
print_separator() {
  printf '%*s\n' "${COLUMNS:-80}" '' | tr ' ' '='
}

print_separator
echo "🧪 Checking Minikube status..."
print_separator

if ! minikube status >/dev/null 2>&1; then
  echo "⚠️ Minikube is not running. Starting Minikube..."
  if ! minikube start; then
    echo "❌ Failed to start Minikube. Exiting."
    exit 1
  fi
else
  echo "✅ Minikube is already running."
fi

print_separator
echo "🧹 Deleting Kubernetes resources in namespace '$NAMESPACE'..."
print_separator

kubectl delete -f "${CONFIG_DIR}/configmap-template.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/deployment.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/secret.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/service.yaml" -n "$NAMESPACE" --ignore-not-found
kubectl delete -f "${CONFIG_DIR}/ingress.yaml" -n "$NAMESPACE" --ignore-not-found

print_separator
echo "🐳 Removing Docker image '${IMAGE_NAME}' from kind nodes..."
print_separator

# Get all kind node container IDs for the cluster
NODE_CONTAINERS=$(docker ps --filter "name=kind-${CLUSTER_NAME}" --format '{{.ID}}')

if [ -z "$NODE_CONTAINERS" ]; then
  echo "⚠️ No kind nodes found for cluster '${CLUSTER_NAME}'."
else
  for node in $NODE_CONTAINERS; do
    echo "🛑 Removing image from node container $node ..."
    docker exec "$node" crictl rmi "$IMAGE_NAME" || docker exec "$node" docker rmi "$IMAGE_NAME" || echo "⚠️ Image not found or could not be removed on node $node"
  done
fi

print_separator
read -r -p "🛑 Do you want to stop (shut down) Minikube now? (y/N): " stop_mk
print_separator

if [[ "$stop_mk" =~ ^[Yy]$ ]]; then
  echo "📴 Stopping Minikube..."
  minikube stop
  echo "✅ Minikube stopped."
else
  echo "🟢 Minikube left running."
fi

print_separator
echo "✅ Cleanup complete for namespace '$NAMESPACE'."
print_separator
