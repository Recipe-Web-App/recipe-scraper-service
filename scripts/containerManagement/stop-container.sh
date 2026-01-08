#!/bin/bash
# scripts/containerManagement/stop-container.sh
# Scale down recipe-scraper-service deployments to 0

set -euo pipefail

NAMESPACE="recipe-scraper-dev"

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
echo -e "${CYAN}Stopping recipe-scraper-service...${NC}"
print_separator "-"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  print_status "warning" "Namespace '$NAMESPACE' does not exist. Nothing to stop."
  exit 0
fi

print_separator "="
echo -e "${CYAN}Scaling deployments to 0...${NC}"
print_separator "-"

kubectl scale deployment/recipe-scraper-service -n "$NAMESPACE" --replicas=0
kubectl scale deployment/recipe-scraper-worker -n "$NAMESPACE" --replicas=0

print_status "ok" "Scale down commands issued"

print_separator "="
echo -e "${CYAN}Waiting for pods to terminate...${NC}"
print_separator "-"

# Wait for pods to be deleted
kubectl wait --namespace="$NAMESPACE" \
  --for=delete pod \
  --selector=app.kubernetes.io/name=recipe-scraper-service \
  --timeout=60s 2>/dev/null || true

print_separator "="
echo -e "${CYAN}Current Pod Status:${NC}"
print_separator "-"

kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "No pods running"

print_separator "="
print_status "ok" "Containers stopped!"
echo ""
echo "To start again: ./scripts/containerManagement/start-container.sh"
