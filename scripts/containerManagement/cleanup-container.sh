#!/bin/bash
# scripts/containerManagement/cleanup-container.sh
# Delete all recipe-scraper-service resources from minikube

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

print_separator "="
echo -e "${CYAN}Cleaning up recipe-scraper-service...${NC}"
print_separator "-"

# Check for --remove-image flag
REMOVE_IMAGE=false
if [[ "${1:-}" == "--remove-image" ]]; then
  REMOVE_IMAGE=true
fi

print_separator "="
echo -e "${CYAN}Deleting namespace '$NAMESPACE'...${NC}"
print_separator "-"

if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  kubectl delete namespace "$NAMESPACE" --wait=true
  print_status "ok" "Namespace '$NAMESPACE' deleted"
else
  print_status "warning" "Namespace '$NAMESPACE' does not exist"
fi

if $REMOVE_IMAGE; then
  print_separator "="
  echo -e "${CYAN}Removing image from Minikube...${NC}"
  print_separator "-"

  minikube ssh "docker rmi -f $FULL_IMAGE_NAME" 2>/dev/null || true
  print_status "ok" "Image removed from Minikube"
fi

print_separator "="
print_status "ok" "Cleanup complete!"
echo ""
echo "To redeploy: ./scripts/containerManagement/deploy-container.sh"
echo ""
echo "Options:"
echo "  --remove-image  Also remove the Docker image from Minikube"
