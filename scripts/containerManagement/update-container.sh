#!/bin/bash
# scripts/containerManagement/update-container.sh
# Rebuild and redeploy recipe-scraper-service in minikube

set -euo pipefail

NAMESPACE="recipe-scraper-dev"
IMAGE_NAME="ghcr.io/recipe-web-app/recipe-scraper-service"
IMAGE_TAG="develop"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

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

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

print_separator "="
echo -e "${CYAN}Updating recipe-scraper-service...${NC}"
print_separator "-"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  print_status "error" "Namespace '$NAMESPACE' does not exist. Run deploy-container.sh first."
  exit 1
fi

print_separator "="
echo -e "${CYAN}Rebuilding Docker image: ${FULL_IMAGE_NAME}${NC}"
print_separator "-"

docker build -t "$FULL_IMAGE_NAME" .
print_status "ok" "Docker image rebuilt successfully"

print_separator "="
echo -e "${CYAN}Removing old image from Minikube...${NC}"
print_separator "-"

minikube ssh "docker rmi -f $FULL_IMAGE_NAME" 2>/dev/null || true
print_status "ok" "Old image removed"

print_separator "="
echo -e "${CYAN}Loading new image into Minikube...${NC}"
print_separator "-"

minikube image load "$FULL_IMAGE_NAME"
print_status "ok" "New image loaded"

print_separator "="
echo -e "${CYAN}Triggering rollout restart...${NC}"
print_separator "-"

kubectl rollout restart deployment/recipe-scraper-service -n "$NAMESPACE"
kubectl rollout restart deployment/recipe-scraper-worker -n "$NAMESPACE"
print_status "ok" "Rollout restart triggered"

print_separator "="
echo -e "${CYAN}Waiting for rollout to complete...${NC}"
print_separator "-"

kubectl rollout status deployment/recipe-scraper-service -n "$NAMESPACE" --timeout=120s || true
kubectl rollout status deployment/recipe-scraper-worker -n "$NAMESPACE" --timeout=120s || true

print_separator "="
echo -e "${CYAN}Current Pod Status:${NC}"
print_separator "-"

kubectl get pods -n "$NAMESPACE"

print_separator "="
print_status "ok" "Update complete!"
