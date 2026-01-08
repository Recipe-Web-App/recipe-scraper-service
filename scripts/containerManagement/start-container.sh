#!/bin/bash
# scripts/containerManagement/start-container.sh
# Scale up recipe-scraper-service deployments

set -euo pipefail

NAMESPACE="recipe-scraper-dev"
API_REPLICAS="${1:-1}"
WORKER_REPLICAS="${2:-1}"

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

print_separator "="
echo -e "${CYAN}Starting recipe-scraper-service...${NC}"
print_separator "-"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  print_status "error" "Namespace '$NAMESPACE' does not exist. Run deploy-container.sh first."
  exit 1
fi

print_separator "="
echo -e "${CYAN}Scaling deployments...${NC}"
print_separator "-"

echo "  API replicas: $API_REPLICAS"
echo "  Worker replicas: $WORKER_REPLICAS"
echo ""

kubectl scale deployment/recipe-scraper-service -n "$NAMESPACE" --replicas="$API_REPLICAS"
kubectl scale deployment/recipe-scraper-worker -n "$NAMESPACE" --replicas="$WORKER_REPLICAS"

print_status "ok" "Scale commands issued"

print_separator "="
echo -e "${CYAN}Waiting for pods to be ready...${NC}"
print_separator "-"

kubectl wait --namespace="$NAMESPACE" \
  --for=condition=Available deployment/recipe-scraper-service \
  --timeout=90s || true

kubectl wait --namespace="$NAMESPACE" \
  --for=condition=Available deployment/recipe-scraper-worker \
  --timeout=90s || true

print_separator "="
echo -e "${CYAN}Current Pod Status:${NC}"
print_separator "-"

kubectl get pods -n "$NAMESPACE"

print_separator "="
print_status "ok" "Containers started!"
echo ""
echo "Usage: $0 [api_replicas] [worker_replicas]"
echo "  Default: 1 replica each"
