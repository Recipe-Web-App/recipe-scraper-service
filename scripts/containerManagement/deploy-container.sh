#!/bin/bash
# scripts/containerManagement/deploy-container.sh
# Deploy recipe-scraper-service to minikube using Kustomize

set -euo pipefail

NAMESPACE="recipe-scraper-dev"
IMAGE_NAME="ghcr.io/recipe-web-app/recipe-scraper-service"
IMAGE_TAG="develop"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
OVERLAY_PATH="k8s/overlays/development"

COLUMNS=$(tput cols 2>/dev/null || echo 80)

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_separator() {
  local char="${1:-=}"
  local width="${COLUMNS:-80}"
  printf '%*s\n' "$width" '' | tr ' ' "$char"
}

print_status() {
  local status="$1"
  local message="$2"
  if [ "$status" = "ok" ]; then
    echo -e "${GREEN}[OK]${NC} $message"
  elif [ "$status" = "warning" ]; then
    echo -e "${YELLOW}[WARN]${NC} $message"
  else
    echo -e "${RED}[ERROR]${NC} $message"
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

print_separator "="
echo -e "${CYAN}Checking prerequisites...${NC}"
print_separator "-"

env_status=true
for cmd in minikube kubectl docker kustomize; do
  if command_exists "$cmd"; then
    print_status "ok" "$cmd is installed"
  else
    print_status "error" "$cmd is not installed"
    env_status=false
  fi
done

if ! $env_status; then
  echo "Please resolve the above issues before proceeding."
  exit 1
fi

print_separator "="
echo -e "${CYAN}Checking Minikube status...${NC}"
print_separator "-"

if ! minikube status >/dev/null 2>&1; then
  echo -e "${YELLOW}Starting Minikube...${NC}"
  minikube start
else
  print_status "ok" "Minikube is already running"
fi

print_separator "="
echo -e "${CYAN}Building Docker image directly in Minikube: ${FULL_IMAGE_NAME}${NC}"
print_separator "-"

# Build directly in Minikube's Docker daemon (most reliable method)
eval "$(minikube docker-env)"
docker build -t "$FULL_IMAGE_NAME" --target development .
print_status "ok" "Docker image built in Minikube"

# Reset to host Docker daemon
eval "$(minikube docker-env --unset)"

print_separator "="
echo -e "${CYAN}Deploying with Kustomize...${NC}"
print_separator "-"

# Delete existing namespace if present (clean deployment)
kubectl delete namespace "$NAMESPACE" --ignore-not-found --wait=true 2>/dev/null || true

# Apply Kustomize overlay
kustomize build --load-restrictor LoadRestrictionsNone "$OVERLAY_PATH" | kubectl apply -f -
print_status "ok" "Kustomize manifests applied"

print_separator "="
echo -e "${CYAN}Waiting for pods to be ready...${NC}"
print_separator "-"

# Wait for API deployment
kubectl wait --namespace="$NAMESPACE" \
  --for=condition=Available deployment/recipe-scraper-service \
  --timeout=120s || true

# Wait for worker deployment
kubectl wait --namespace="$NAMESPACE" \
  --for=condition=Available deployment/recipe-scraper-worker \
  --timeout=120s || true

print_separator "="
echo -e "${CYAN}Deployment Status:${NC}"
print_separator "-"

kubectl get pods -n "$NAMESPACE"

print_separator "="
echo -e "${CYAN}Access Information:${NC}"
print_separator "-"

echo "  Namespace: $NAMESPACE"
echo "  Image: $FULL_IMAGE_NAME"
echo ""
echo "  Port forward to access API:"
echo "    kubectl port-forward -n $NAMESPACE svc/recipe-scraper-service 8080:80"
echo ""
echo "  Then access:"
echo "    Health: http://localhost:8080/api/v1/recipe-scraper/health"
echo "    Docs:   http://localhost:8080/docs"
echo ""
echo "  View logs:"
echo "    kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=api -f"
echo ""

print_separator "="
print_status "ok" "Deployment complete!"
